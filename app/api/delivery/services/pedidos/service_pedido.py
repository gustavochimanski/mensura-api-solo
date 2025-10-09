from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from math import radians, cos, sin, asin, sqrt

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
from app.api.delivery.models.model_pedido_item_dv import PedidoItemModel
from app.api.delivery.repositories.repo_entregadores import EntregadorRepository
from app.api.delivery.repositories.repo_pedidos import PedidoRepository
from app.api.delivery.schemas.schema_cliente import ClienteOut
from app.api.delivery.schemas.schema_cupom import CupomOut
from app.api.delivery.schemas.schema_endereco import EnderecoOut
from app.api.delivery.schemas.schema_entregador import EntregadorOut
from app.api.delivery.schemas.schema_meio_pagamento import MeioPagamentoResponse, MeioPagamentoTipoEnum
from app.api.delivery.schemas.schema_pedido import (
    EditarPedidoRequest,
    EnderecoPedidoDetalhe,
    FinalizarPedidoRequest,
    ItemPedidoEditar,
    ItemPedidoRequest,
    ItemPedidoResponse,
    PedidoKanbanResponse,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoComEndereco,
    PedidoResponseCompletoTotal,
    PedidoResponseSimplificado,
)
from app.api.delivery.schemas.schema_pedido_status_historico import (
    PedidoStatusHistoricoOut,
)
from app.api.delivery.schemas.schema_shared_enums import (
    OrigemPedidoEnum,
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
    PedidoStatusEnum,
    TipoEntregaEnum,
)
from app.api.delivery.schemas.schema_transacao_pagamento import TransacaoResponse
from app.api.delivery.services.meio_pagamento_service import MeioPagamentoService
from app.api.delivery.services.pagamento.service_pagamento import PagamentoService
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.schema_empresa import EmpresaResponse
from app.utils.logger import logger
from app.utils.database_utils import now_trimmed
#

QTD_MAX_ITENS = 200


def _dec(value: float | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PedidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.repo_entregador = EntregadorRepository(db)
        self.pagamentos = PagamentoService(db)
        self._cache_regioes = {}  # Cache simples para regiões

    # ---------------- Helpers ----------------
    def _pedido_to_response(self, pedido: PedidoDeliveryModel) -> PedidoResponse:
        return PedidoResponse(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente_id=pedido.cliente.id if pedido.cliente else None,
            telefone_cliente=pedido.cliente.telefone if pedido.cliente else None,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                        else OrigemPedidoEnum(pedido.origem),
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario),
                    observacao=it.observacao,
                    produto_descricao_snapshot=it.produto_descricao_snapshot,
                    produto_imagem_snapshot=it.produto_imagem_snapshot,
                )
                for it in pedido.itens
            ],
            transacao=TransacaoResponse.model_validate(pedido.transacao) if pedido.transacao else None,
        )

    def _calcular_taxas(
        self,
        *,
        tipo_entrega: TipoEntregaEnum,
        subtotal: Decimal,
        endereco=None,
        empresa_id: int | None = None,
    ) -> tuple[Decimal, Decimal]:
        from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel

        taxa_entrega = _dec(0)
        if tipo_entrega == TipoEntregaEnum.DELIVERY and endereco and empresa_id:
            # Verifica se existem regiões cadastradas para a empresa
            if not self._verificar_regioes_cadastradas(empresa_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Nenhuma região de entrega cadastrada para esta empresa."
                )
            
            # Validações básicas do endereço
            if not endereco.bairro or not endereco.cidade or not endereco.estado:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Endereço incompleto. Bairro, cidade e estado são obrigatórios para delivery."
                )

            # Busca região por bairro, cidade e estado
            regiao_encontrada = self._buscar_regiao_por_bairro(
                endereco.bairro, endereco.cidade, endereco.estado, empresa_id
            )
            
            # Se não encontrou por bairro, tenta busca por CEP
            if not regiao_encontrada and endereco.cep:
                regiao_encontrada = self._buscar_regiao_por_cep(
                    endereco.cep, empresa_id
                )

            if not regiao_encontrada:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Não entregamos no bairro {endereco.bairro}, {endereco.cidade}-{endereco.estado}"
                )

            taxa_entrega = _dec(regiao_encontrada.taxa_entrega)

        taxa_servico = (subtotal * Decimal("0.01")).quantize(Decimal("0.01"))
        return taxa_entrega, taxa_servico

    def _buscar_regiao_por_bairro(self, bairro: str, cidade: str, estado: str, empresa_id: int):
        """Busca região por bairro, cidade e estado - método principal simplificado"""
        from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
        
        if not (bairro and cidade and estado):
            return None
        
        # Limpa e normaliza os dados
        bairro_limpo = bairro.strip().upper()
        cidade_limpa = cidade.strip().upper()
        estado_limpo = estado.strip().upper()
        
        # Busca exata primeiro
        regiao = (
                self.db.query(RegiaoEntregaModel)
                .filter(
                    RegiaoEntregaModel.empresa_id == empresa_id,
                    RegiaoEntregaModel.ativo == True,
                RegiaoEntregaModel.bairro == bairro_limpo,
                RegiaoEntregaModel.cidade == cidade_limpa,
                RegiaoEntregaModel.uf == estado_limpo
            )
            .first()
        )
        
        # Se não encontrou exato, tenta busca com LIKE (mais flexível)
        if not regiao:
            regiao = (
                self.db.query(RegiaoEntregaModel)
                .filter(
                    RegiaoEntregaModel.empresa_id == empresa_id,
                    RegiaoEntregaModel.ativo == True,
                    RegiaoEntregaModel.bairro.ilike(f"%{bairro_limpo}%"),
                    RegiaoEntregaModel.cidade.ilike(f"%{cidade_limpa}%"),
                    RegiaoEntregaModel.uf == estado_limpo
                )
                .first()
            )
        
        return regiao

    def _buscar_regiao_por_cep(self, cep: str, empresa_id: int):
        """Busca região por CEP exato - método de fallback"""
        from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
        
        if not cep:
            return None
            
        cep_limpo = cep.replace('-', '').replace(' ', '')
        
        regiao = (
            self.db.query(RegiaoEntregaModel)
            .filter(
                RegiaoEntregaModel.empresa_id == empresa_id,
                RegiaoEntregaModel.ativo == True,
                RegiaoEntregaModel.cep == cep_limpo
            )
            .first()
        )
        
        return regiao

    def _verificar_regioes_cadastradas(self, empresa_id: int) -> bool:
        """Verifica se existem regiões de entrega cadastradas para a empresa"""
        from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
        
        cache_key = f"regioes_empresa_{empresa_id}"
        if cache_key in self._cache_regioes:
            return self._cache_regioes[cache_key]
        
        count = (
            self.db.query(RegiaoEntregaModel)
            .filter(
                RegiaoEntregaModel.empresa_id == empresa_id,
                RegiaoEntregaModel.ativo == True
            )
            .count()
        )
        
        has_regions = count > 0
        self._cache_regioes[cache_key] = has_regions
        return has_regions

    def limpar_cache_regioes(self, empresa_id: int = None):
        """Limpa o cache de regiões para uma empresa específica ou todas"""
        if empresa_id:
            cache_key = f"regioes_empresa_{empresa_id}"
            self._cache_regioes.pop(cache_key, None)
        else:
            self._cache_regioes.clear()

    def _aplicar_cupom(
        self,
        *,
        cupom_id: Optional[int],
        subtotal: Decimal,
        empresa_id: int,
    ) -> Decimal:
        if not cupom_id:
            return _dec(0)
        cupom = self.repo.get_cupom(cupom_id)
        if not cupom or not cupom.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom inválido ou inativo")
        if cupom.empresa_id != empresa_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom não pertence a esta empresa")

        # validade e mínimo
        if cupom.validade_inicio and cupom.validade_fim:
            from datetime import datetime, timezone
            now = datetime.now(tz=timezone.utc)
            if not (cupom.validade_inicio <= now <= cupom.validade_fim):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom fora de validade")
        if cupom.minimo_compra and subtotal < cupom.minimo_compra:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subtotal abaixo do mínimo do cupom")

        desconto = Decimal("0")
        if cupom.desconto_valor:
            desconto += _dec(cupom.desconto_valor)
        if cupom.desconto_percentual:
            desconto += (subtotal * (Decimal(cupom.desconto_percentual) / Decimal("100"))).quantize(Decimal("0.01"))

        return min(desconto, subtotal)

    def _deve_usar_gateway(self, metodo: PagamentoMetodoEnum) -> bool:
        """Determina se o método de pagamento deve usar o gateway de pagamento."""
        return metodo == PagamentoMetodoEnum.PIX_ONLINE

    def verificar_endereco_em_uso(self, endereco_id: int) -> bool:
        """Verifica se um endereço está sendo usado em pedidos ativos (não cancelados/entregues)."""
        pedidos_ativos = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                PedidoDeliveryModel.endereco_id == endereco_id,
                PedidoDeliveryModel.status.in_(["P", "I", "R", "S", "D"])  # Pendente, Pendente Impressão, Em preparo, Saiu para entrega, Em edição
            )
            .count()
        )
        return pedidos_ativos > 0

    def get_pedidos_por_regiao(self, latitude_centro: float, longitude_centro: float, raio_km: float = 5.0):
        """
        Retorna pedidos dentro de uma região geográfica específica usando PostGIS.
        Muito mais eficiente que cálculos manuais de distância.
        """
        from sqlalchemy import text
        
        # Cria ponto central
        ponto_centro = f"ST_GeomFromText('POINT({longitude_centro} {latitude_centro})', 4326)"
        
        # Converte raio de km para metros
        raio_metros = raio_km * 1000
        
        # Query usando PostGIS ST_DWithin (muito mais eficiente)
        query = text(f"""
            SELECT p.*, 
                   ST_Distance(p.endereco_geography, {ponto_centro}) as distancia_metros
            FROM delivery.pedidos_dv p
            WHERE p.endereco_geography IS NOT NULL
              AND ST_DWithin(p.endereco_geography, {ponto_centro}, :raio_metros)
            ORDER BY distancia_metros
        """)
        
        result = self.db.execute(query, {"raio_metros": raio_metros})
        
        pedidos_na_regiao = []
        for row in result:
            pedido = self.db.query(PedidoDeliveryModel).filter_by(id=row.id).first()
            if pedido:
                pedidos_na_regiao.append({
                    "pedido": pedido,
                    "distancia_km": row.distancia_metros / 1000  # Converte para km
                })
        
        return pedidos_na_regiao

    def get_pedidos_por_poligono(self, coordenadas_poligono: list):
        """
        Retorna pedidos dentro de um polígono específico.
        Útil para análise por bairros, regiões administrativas, etc.
        """
        from sqlalchemy import text
        
        # Formata coordenadas como polígono WKT
        coords_str = ", ".join([f"{lon} {lat}" for lon, lat in coordenadas_poligono])
        poligono_wkt = f"POLYGON(({coords_str}))"
        
        query = text("""
            SELECT p.*
            FROM delivery.pedidos_dv p
            WHERE p.endereco_geo IS NOT NULL
              AND ST_Within(p.endereco_geo, ST_GeomFromText(:poligono, 4326))
        """)
        
        result = self.db.execute(query, {"poligono": poligono_wkt})
        
        pedidos = []
        for row in result:
            pedido = self.db.query(PedidoDeliveryModel).filter_by(id=row.id).first()
            if pedido:
                pedidos.append(pedido)
        
        return pedidos

    def _recalcular_pedido(self, pedido: PedidoDeliveryModel):
        """Recalcula subtotal, desconto, taxas e valor total do pedido e salva no banco."""
        subtotal = self.db.query(
            func.sum(PedidoItemModel.quantidade * PedidoItemModel.preco_unitario)
        ).filter(PedidoItemModel.pedido_id == pedido.id).scalar() or Decimal("0")

        subtotal = Decimal(subtotal)  # força Decimal
        desconto = self._aplicar_cupom(
            cupom_id=pedido.cupom_id,
            subtotal=subtotal,
            empresa_id=pedido.empresa_id,
        )

        endereco = pedido.endereco  # relacionamento
        taxa_entrega, taxa_servico = self._calcular_taxas(
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            subtotal=subtotal,
            endereco=endereco,
            empresa_id=pedido.empresa_id,
        )

        self.repo.atualizar_totais(
            pedido,
            subtotal=subtotal,
            desconto=desconto,
            taxa_entrega=taxa_entrega,
            taxa_servico=taxa_servico,
        )
        # sem refresh aqui; manter estado consistente
        self.repo.commit()
        # recarrega para resposta com relacionamentos
        self.db.refresh(pedido)

    # ---------------- Fluxos ----------------
    async def finalizar_pedido(self, payload: FinalizarPedidoRequest, cliente_id: int) -> PedidoResponse:
        # Validações
        if not payload.itens:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if len(payload.itens) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        meio_pagamento = None
        if payload.meio_pagamento_id:
            meio_pagamento = MeioPagamentoService(self.db).get(payload.meio_pagamento_id)
            if not meio_pagamento or not meio_pagamento.ativo:
                raise HTTPException(400, "Meio de pagamento inválido ou inativo")

        empresa = self.repo_empresa.get_empresa_by_id(payload.empresa_id)
        if not empresa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        cliente = self.repo.get_cliente_by_id(cliente_id)
        if not cliente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

        if payload.tipo_entrega == TipoEntregaEnum.DELIVERY and not payload.endereco_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço é obrigatório para delivery")

        endereco = None
        endereco_snapshot = None
        endereco_geo = None
        endereco_latitude = None
        endereco_longitude = None
        if payload.endereco_id:
            endereco = self.repo.get_endereco(payload.endereco_id)
            if not endereco or endereco.cliente_id != cliente_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço inválido para o cliente")
            
            # Extrai coordenadas para relatórios geográficos
            endereco_latitude = float(endereco.latitude) if endereco.latitude else None
            endereco_longitude = float(endereco.longitude) if endereco.longitude else None
            
            # Cria ponto geográfico para consultas PostGIS
            if endereco_latitude and endereco_longitude:
                from geoalchemy2 import WKTElement
                endereco_geo = WKTElement(f'POINT({endereco_longitude} {endereco_latitude})', srid=4326)
            
            # Cria snapshot do endereço para preservar dados no momento do pedido
            endereco_snapshot = {
                "id": endereco.id,
                "logradouro": endereco.logradouro,
                "numero": endereco.numero,
                "complemento": endereco.complemento,
                "bairro": endereco.bairro,
                "cidade": endereco.cidade,
                "estado": endereco.estado,
                "cep": endereco.cep,
                "latitude": endereco_latitude,
                "longitude": endereco_longitude,
                "is_principal": endereco.is_principal,
                "cliente_id": endereco.cliente_id,
                "snapshot_em": str(now_trimmed())
            }

        try:
            status_inicial = (
                PedidoStatusEnum.A.value
                if self._is_pix_online_meio_pagamento(meio_pagamento)
                else PedidoStatusEnum.I.value
            )

            # CRIA PEDIDO — garante cliente_id persistido de cara
            pedido = self.repo.criar_pedido(
                cliente_id=cliente.id,  # usar o ID obtido do banco
                empresa_id=payload.empresa_id,
                endereco_id=payload.endereco_id,
                meio_pagamento_id=payload.meio_pagamento_id,
                status=status_inicial,
                tipo_entrega=payload.tipo_entrega.value if hasattr(payload.tipo_entrega, "value") else payload.tipo_entrega,
                origem=payload.origem.value if hasattr(payload.origem, "value") else payload.origem,
                endereco_snapshot=endereco_snapshot,
                endereco_geo=endereco_geo,  # Corrigido: usar endereco_geo em vez de coordenadas separadas
            )

            logger.info(f"[finalizar_pedido] criado pedido_id={pedido.id} cliente_id={pedido.cliente_id}")

            # ITENS
            subtotal = Decimal("0")
            for it in payload.itens:
                pe = self.repo.get_produto_emp(payload.empresa_id, it.produto_cod_barras)
                if not pe:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
                if not pe.disponivel or not (pe.produto and pe.produto.ativo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")

                preco = _dec(pe.preco_venda)
                subtotal += preco * it.quantidade
                self.repo.adicionar_item(
                    pedido_id=pedido.id,  # ⚠️ apenas FK; não passar o objeto pedido junto
                    cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=preco,
                    observacao=it.observacao,
                    produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                    produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
                )

            # TOTAIS
            desconto = self._aplicar_cupom(
                cupom_id=payload.cupom_id,
                subtotal=subtotal,
                empresa_id=payload.empresa_id,
            )
            taxa_entrega, taxa_servico = self._calcular_taxas(
                tipo_entrega=payload.tipo_entrega if isinstance(payload.tipo_entrega, TipoEntregaEnum)
                            else TipoEntregaEnum(payload.tipo_entrega),
                subtotal=subtotal,
                endereco=endereco,
                empresa_id=payload.empresa_id,
            )

            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
            )

            # DEMAIS CAMPOS
            pedido.observacao_geral = payload.observacao_geral
            if payload.troco_para:
                pedido.troco_para = _dec(payload.troco_para)

            logger.info(f"[finalizar_pedido] antes commit cliente_id={pedido.cliente_id}")
            self.repo.commit()
            logger.info(f"[finalizar_pedido] após commit cliente_id={pedido.cliente_id}")

            # Se for PIX_ONLINE, cria/atualiza transação no gateway sem alterar status do pedido
            if self._is_pix_online_meio_pagamento(meio_pagamento):
                try:
                    await self.pagamentos.iniciar_transacao(
                        pedido_id=pedido.id,
                        meio_pagamento_id=pedido.meio_pagamento_id,
                        valor=_dec(pedido.valor_total),
                        metodo=PagamentoMetodoEnum.PIX_ONLINE,
                        gateway=PagamentoGatewayEnum.MERCADOPAGO,
                        metadata={"pedido_id": pedido.id, "empresa_id": pedido.empresa_id},
                    )
                    pedido = self.repo.get_pedido(pedido.id)
                except Exception as e:
                    logger.error(f"Erro ao iniciar transação PIX_ONLINE: {e}")

            # Recarrega fresco para resposta (com cliente/endereço/meio_pagamento)
            pedido = self.repo.get_pedido(pedido.id)
            logger.info(f"[finalizar_pedido] get_pedido cliente_id={pedido.cliente_id if pedido else None}")

        except HTTPException:
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao finalizar pedido: {e}")

        return self._pedido_to_response(pedido)

    async def confirmar_pagamento(
        self,
        *,
        pedido_id: int,
        metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
        gateway: PagamentoGatewayEnum = None,
    ) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        if pedido.valor_total is None or pedido.valor_total <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Valor total inválido para pagamento")

        # idempotência simples
        if pedido.transacao and pedido.transacao.status in ("PAGO", "AUTORIZADO"):
            return self._pedido_to_response(pedido)

        # Determina o gateway baseado no método de pagamento
        if gateway is None:
            if self._deve_usar_gateway(metodo):
                gateway = PagamentoGatewayEnum.PIX_INTERNO  # ou outro gateway de PIX online
            else:
                gateway = PagamentoGatewayEnum.PIX_INTERNO

        try:
            tx = self.repo.criar_transacao_pagamento(
                pedido_id=pedido.id,
                meio_pagamento_id=pedido.meio_pagamento_id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=_dec(pedido.valor_total),
            )

            # Se deve usar gateway, chama o gateway de pagamento
            if self._deve_usar_gateway(metodo):
                result = await self.gateway.charge(
                    order_id=pedido.id,
                    amount=_dec(pedido.valor_total),
                    metodo=metodo,
                    gateway=gateway,
                    metadata={"empresa_id": pedido.empresa_id},
                )
            else:
                # Para outros métodos, simula pagamento direto (sem gateway)
                result = PaymentResult(
                    status=PagamentoStatusEnum.PAGO,
                    provider_transaction_id=f"direct_{pedido.id}_{metodo.value}",
                    payload={"metodo": metodo.value, "gateway": "DIRETO"},
                    qr_code=None,
                    qr_code_base64=None,
                )

            if result.status == PagamentoStatusEnum.PAGO:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="PAGO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                    qr_code=result.qr_code,
                    qr_code_base64=result.qr_code_base64,
                    timestamp_field="pago_em",
                )
                atualizar_para = PedidoStatusEnum.I.value if metodo == PagamentoMetodoEnum.PIX_ONLINE else PedidoStatusEnum.A.value
                self.repo.atualizar_status_pedido(pedido, atualizar_para, motivo="Pagamento confirmado")
            else:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="RECUSADO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                )

            self.repo.commit()
            pedido = self.repo.get_pedido(pedido.id)
            return self._pedido_to_response(pedido)

        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao confirmar pagamento: {e}")

    # --------------- Consultas ---------------
    def listar_pedidos(self, cliente_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponse]:
        pedidos = (
            self.repo.db.query(PedidoDeliveryModel)
            .filter(PedidoDeliveryModel.cliente_id == cliente_id)
            .order_by(PedidoDeliveryModel.data_criacao.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [self._pedido_to_response(p) for p in pedidos]


    def listar_pedidos_completo(self, cliente_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponseSimplificado]:
        """
        Lista pedidos com dados simplificados incluindo nome do meio de pagamento
        """
        from sqlalchemy.orm import joinedload
        
        pedidos = (
            self.repo.db.query(PedidoDeliveryModel)
            .options(
                joinedload(PedidoDeliveryModel.cliente),
                joinedload(PedidoDeliveryModel.meio_pagamento)
            )
            .filter(PedidoDeliveryModel.cliente_id == cliente_id)
            .order_by(PedidoDeliveryModel.data_criacao.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [self._pedido_to_response_simplificado(p) for p in pedidos]

    def get_pedido_by_id(self, pedido_id: int) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response(pedido)

    def _pedido_to_response_completo(self, pedido: PedidoDeliveryModel) -> PedidoResponseCompleto:
        return PedidoResponseCompleto(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente=ClienteOut.model_validate(pedido.cliente) if pedido.cliente else None,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                        else OrigemPedidoEnum(pedido.origem),
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ]
        )

    def get_pedido_by_id_completo(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response_completo(pedido)

    def _pedido_to_response_completo_com_endereco(self, pedido: PedidoDeliveryModel) -> PedidoResponseCompletoComEndereco:
        return PedidoResponseCompletoComEndereco(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente=ClienteOut.model_validate(pedido.cliente) if pedido.cliente else None,
            endereco=EnderecoOut.model_validate(pedido.endereco) if pedido.endereco else None,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                        else OrigemPedidoEnum(pedido.origem),
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ]
        )

    def _build_endereco_selecionado(self, pedido: PedidoDeliveryModel) -> EnderecoOut | dict | None:
        if pedido.endereco_snapshot:
            return pedido.endereco_snapshot

        if pedido.endereco:
            return EnderecoOut.model_validate(pedido.endereco)

        return None

    def _build_outros_enderecos(self, pedido: PedidoDeliveryModel) -> list[EnderecoOut | dict]:
        if not pedido.cliente or not getattr(pedido.cliente, "enderecos", None):
            return []

        endereco_id_selecionado = None
        if pedido.endereco_snapshot and isinstance(pedido.endereco_snapshot, dict):
            endereco_id_selecionado = pedido.endereco_snapshot.get("id")
        elif pedido.endereco_id:
            endereco_id_selecionado = pedido.endereco_id

        outros = []
        for endereco in pedido.cliente.enderecos:
            if endereco_id_selecionado and getattr(endereco, "id", None) == endereco_id_selecionado:
                continue
            outros.append(EnderecoOut.model_validate(endereco))

        return outros

    def get_pedido_by_id_completo_com_endereco(self, pedido_id: int) -> PedidoResponseCompletoComEndereco:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response_completo_com_endereco(pedido)

    def _pedido_to_response_completo_total(self, pedido: PedidoDeliveryModel) -> PedidoResponseCompletoTotal:
        return PedidoResponseCompletoTotal(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente=ClienteOut.model_validate(pedido.cliente) if pedido.cliente else None,
            endereco=EnderecoPedidoDetalhe(
                endereco_selecionado=self._build_endereco_selecionado(pedido),
            outros_enderecos=self._build_outros_enderecos(pedido),
            ),
            empresa=EmpresaResponse.model_validate(pedido.empresa) if pedido.empresa else None,
            entregador=EntregadorOut.model_validate(pedido.entregador) if pedido.entregador else None,
            meio_pagamento=MeioPagamentoResponse.model_validate(pedido.meio_pagamento) if pedido.meio_pagamento else None,
            cupom=CupomOut.model_validate(pedido.cupom) if pedido.cupom else None,
            transacao=TransacaoResponse.model_validate(pedido.transacao) if pedido.transacao else None,
            historicos=[PedidoStatusHistoricoOut.model_validate(h) for h in pedido.historicos] if pedido.historicos else [],
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                        else OrigemPedidoEnum(pedido.origem),
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ]
        )

    def get_pedido_by_id_completo_total(self, pedido_id: int) -> PedidoResponseCompletoTotal:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response_completo_total(pedido)

    def _pedido_to_response_simplificado(self, pedido: PedidoDeliveryModel) -> PedidoResponseSimplificado:
        """Converte pedido para formato simplificado com apenas campos essenciais"""
        # Obtém nome do meio de pagamento
        meio_pagamento_nome = None
        if pedido.meio_pagamento:
            meio_pagamento_nome = pedido.meio_pagamento.display()
        
        return PedidoResponseSimplificado(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente_nome=pedido.cliente.nome if pedido.cliente else "Cliente não informado",
            cliente_telefone=pedido.cliente.telefone if pedido.cliente else None,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=it.produto_descricao_snapshot,
                    produto_imagem_snapshot=it.produto_imagem_snapshot
                ) for it in pedido.itens
            ],
            meio_pagamento_nome=meio_pagamento_nome
        )

    # ---------------- Admin / Kanban ----------------
    def list_all_kanban(self, limit: int = 500, date_filter: date | None = None, empresa_id: int = 1):
        pedidos = self.repo.list_all_kanban(limit=limit, date_filter=date_filter, empresa_id=empresa_id)
        resultados = []

        for p in pedidos:
            cliente = p.cliente

            endereco_str = None
            if p.endereco_snapshot:
                snapshot = p.endereco_snapshot
                endereco_str = ", ".join(
                    filter(None, [
                        snapshot.get("logradouro"),
                        snapshot.get("numero"),
                        snapshot.get("bairro"),
                        snapshot.get("cidade"),
                        snapshot.get("cep"),
                        snapshot.get("complemento"),
                    ])
                )
            elif p.endereco:
                endereco_model = p.endereco
                endereco_str = ", ".join(
                    filter(None, [
                        endereco_model.logradouro,
                        endereco_model.numero,
                        endereco_model.bairro,
                        endereco_model.cidade,
                        endereco_model.cep,
                        endereco_model.complemento,
                    ])
                )
            elif cliente and cliente.enderecos:
                endereco_model = cliente.enderecos[0]
                endereco_str = ", ".join(
                    filter(None, [
                        endereco_model.logradouro,
                        endereco_model.numero,
                        endereco_model.bairro,
                        endereco_model.cidade,
                        endereco_model.cep,
                        endereco_model.complemento,
                    ])
                )

            resultados.append(
                PedidoKanbanResponse(
                    id=p.id,
                    status=p.status,
                    cliente_id=cliente.id if cliente else None,
                    valor_total=p.valor_total,
                    data_criacao=p.data_criacao,
                    telefone_cliente=cliente.telefone if cliente else None,
                    nome_cliente=cliente.nome if cliente else None,
                    endereco=endereco_str,
                    meio_pagamento_descricao=p.meio_pagamento.display() if p.meio_pagamento else None,
                    observacao_geral=p.observacao_geral,
                    meio_pagamento_id=p.meio_pagamento.id if p.meio_pagamento else None,
                )
            )

        return resultados

    # ---------------- Atualizações ----------------
    def atualizar_status(self, pedido_id: int, novo_status: PedidoStatusEnum) -> PedidoResponse:
        pedido = self.db.query(PedidoDeliveryModel).filter_by(id=pedido_id).first()
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        pedido.status = novo_status
        self.db.commit()
        self.db.refresh(pedido)
        return self._pedido_to_response(pedido)

    def editar_pedido_parcial(self, pedido_id: int, payload: EditarPedidoRequest) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        if payload.meio_pagamento_id is not None:
            meio_pagamento = MeioPagamentoService(self.db).get(payload.meio_pagamento_id)
            if not meio_pagamento or not meio_pagamento.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")
            pedido.meio_pagamento_id = payload.meio_pagamento_id

        endereco = None
        if payload.endereco_id is not None:
            endereco = self.repo.get_endereco(payload.endereco_id)
            if not endereco:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Endereço não encontrado")
#
            if (
                endereco.cliente_id is not None
                and pedido.cliente_id is not None
                and endereco.cliente_id != pedido.cliente_id
            ):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço não pertence ao cliente do pedido")

            pedido.endereco_id = payload.endereco_id
            pedido.endereco = endereco

            endereco_latitude = float(endereco.latitude) if endereco.latitude else None
            endereco_longitude = float(endereco.longitude) if endereco.longitude else None

            if endereco_latitude and endereco_longitude:
                from geoalchemy2 import WKTElement

                pedido.endereco_geo = WKTElement(
                    f"POINT({endereco_longitude} {endereco_latitude})",
                    srid=4326,
                )
            else:
                pedido.endereco_geo = None

            pedido.endereco_snapshot = {
                "id": endereco.id,
                "logradouro": endereco.logradouro,
                "numero": endereco.numero,
                "complemento": endereco.complemento,
                "bairro": endereco.bairro,
                "cidade": endereco.cidade,
                "estado": endereco.estado,
                "cep": endereco.cep,
                "latitude": endereco_latitude,
                "longitude": endereco_longitude,
                "is_principal": endereco.is_principal,
                "cliente_id": endereco.cliente_id,
                "snapshot_em": str(now_trimmed()),
            }

        if payload.cupom_id is not None:
            pedido.cupom_id = payload.cupom_id

        if payload.observacao_geral is not None:
            pedido.observacao_geral = payload.observacao_geral
        if payload.troco_para is not None:
            pedido.troco_para = _dec(payload.troco_para)

        subtotal = pedido.subtotal or Decimal("0")
        desconto = self._aplicar_cupom(
            cupom_id=pedido.cupom_id,
            subtotal=subtotal,
            empresa_id=pedido.empresa_id,
        )
        taxa_entrega, taxa_servico = self._calcular_taxas(
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            subtotal=subtotal,
            endereco=endereco or pedido.endereco,  # se não veio novo, usa o atual
            empresa_id=pedido.empresa_id,
        )
        self.repo.atualizar_totais(
            pedido,
            subtotal=subtotal,
            desconto=desconto,
            taxa_entrega=taxa_entrega,
            taxa_servico=taxa_servico,
        )

        self.db.flush()
        self._recalcular_pedido(pedido)
        self.repo.commit()
        pedido = self.repo.get_pedido(pedido.id)

        return self._pedido_to_response(pedido)

    def atualizar_item_pedido(self, pedido_id: int, item: ItemPedidoEditar) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        acao = item.acao
        if acao == "atualizar":
            if not item.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "ID do item obrigatório para atualizar")
            it_db = self.repo.get_item_by_id(item.id)
            if not it_db:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item.id} não encontrado")

            if item.quantidade is not None and item.quantidade != it_db.quantidade:
                it_db.quantidade = item.quantidade
            if item.observacao is not None:
                it_db.observacao = item.observacao

        elif acao == "remover":
            if not item.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "ID do item obrigatório para remover")
            it_db = self.repo.get_item_by_id(item.id)
            if not it_db:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item.id} não encontrado")
            self.db.delete(it_db)

        elif acao == "adicionar":
            if not item.produto_cod_barras:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código de barras obrigatório para adicionar")
            if not item.quantidade or item.quantidade <= 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantidade deve ser maior que zero")

            pe = self.repo.get_produto_emp(pedido.empresa_id, item.produto_cod_barras)
            if not pe:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {item.produto_cod_barras} não encontrado")
            if not pe.disponivel or not (pe.produto and pe.produto.ativo):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {item.produto_cod_barras}")

            preco = _dec(pe.preco_venda)
            self.repo.adicionar_item(
                pedido_id=pedido.id,
                cod_barras=item.produto_cod_barras,
                quantidade=item.quantidade,
                preco_unitario=preco,
                observacao=item.observacao,
                produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
            )

        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ação inválida: {acao}")

        self.db.flush()
        self._recalcular_pedido(pedido)
        self.repo.commit()
        pedido = self.repo.get_pedido(pedido.id)

        return self._pedido_to_response(pedido)

    def vincular_entregador(self, pedido_id: int, entregador_id: Optional[int]) -> PedidoResponse:
        """Atualiza `pedidos_dv.entregador_id` diretamente usando SQL UPDATE simples."""
        try:
            stmt = (
                update(PedidoDeliveryModel)
                .where(PedidoDeliveryModel.id == pedido_id)
                .values(entregador_id=entregador_id, data_atualizacao=now_trimmed())
            )
            resultado = self.db.execute(stmt)

            if resultado.rowcount == 0:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

            self.db.commit()

            pedido = self.repo.get_pedido(pedido_id)
            return self._pedido_to_response(pedido)

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.error(f"[vincular_entregador] Falha inesperada: {exc}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao vincular entregador")

    def desvincular_entregador(self, pedido_id: int) -> PedidoResponse:
        """
        Desvincula o entregador atual de um pedido.
        """
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Verifica se o pedido tem entregador vinculado
        if not pedido.entregador_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, 
                "Pedido não possui entregador vinculado"
            )

        # Remove a vinculação
        pedido.entregador_id = None
        self.db.commit()
        self.db.refresh(pedido)

        logger.info(f"[desvincular_entregador] pedido_id={pedido_id}")
        
        return self._pedido_to_response(pedido)

    def testar_busca_regiao(self, bairro: str, cidade: str, estado: str, empresa_id: int) -> dict:
        """
        Método para testar a busca de região por bairro.
        Útil para debugging e validação.
        """
        import time
        from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
        
        resultados = {
            "endereco": {"bairro": bairro, "cidade": cidade, "estado": estado},
            "empresa_id": empresa_id,
            "tempos": {},
            "resultados": {}
        }
        
        # Teste 1: Busca por bairro
        inicio = time.time()
        try:
            regiao_bairro = self._buscar_regiao_por_bairro(bairro, cidade, estado, empresa_id)
            resultados["tempos"]["bairro"] = time.time() - inicio
            resultados["resultados"]["bairro"] = regiao_bairro.id if regiao_bairro else None
        except Exception as e:
            resultados["tempos"]["bairro"] = time.time() - inicio
            resultados["resultados"]["bairro"] = f"Erro: {e}"
        
        # Teste 2: Contagem de regiões
        inicio = time.time()
        count = (
            self.db.query(RegiaoEntregaModel)
            .filter(
                RegiaoEntregaModel.empresa_id == empresa_id,
                RegiaoEntregaModel.ativo == True
            )
            .count()
        )
        resultados["tempos"]["count"] = time.time() - inicio
        resultados["resultados"]["total_regioes"] = count
        
        return resultados

    def alterar_modo_edicao(self, pedido_id: int, modo_edicao: bool) -> PedidoResponse:
        """
        Altera o modo de edição do pedido.
        True = modo edição (status X), False = editado (status D)
        """
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Define o novo status baseado no modo_edicao
        if modo_edicao:
            novo_status = PedidoStatusEnum.X.value  # EM_EDICAO
            motivo = "Modo de edição ativado"
        else:
            novo_status = PedidoStatusEnum.D.value  # EDITADO
            motivo = "Modo de edição finalizado"

        # Atualiza o status do pedido
        self.repo.atualizar_status_pedido(pedido, novo_status, motivo)
        self.repo.commit()

        # Recarrega o pedido para retornar os dados atualizados
        pedido = self.repo.get_pedido(pedido_id)
        return self._pedido_to_response(pedido)

    def _is_pix_online_meio_pagamento(self, meio_pagamento) -> bool:
        if not meio_pagamento:
            return False

        meio_tipo = getattr(meio_pagamento, "tipo", None)
        if isinstance(meio_tipo, MeioPagamentoTipoEnum):
            return meio_tipo == MeioPagamentoTipoEnum.PIX_ONLINE

        if isinstance(meio_pagamento, dict):
            return meio_pagamento.get("tipo") == MeioPagamentoTipoEnum.PIX_ONLINE

        return meio_tipo == "PIX_ONLINE"
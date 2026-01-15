from __future__ import annotations

import asyncio
import threading
from datetime import date
from decimal import Decimal
from typing import Callable, Optional, TYPE_CHECKING
from urllib.parse import quote_plus

from sqlalchemy import func, text, update
from sqlalchemy.orm import Session, joinedload

from fastapi import HTTPException, status

from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoEntrega,
    StatusPedido,
)
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.cadastros.repositories.repo_entregadores import EntregadorRepository
from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum
from app.api.pedidos.schemas.schema_pedido import (
    EditarPedidoRequest,
    FinalizarPedidoRequest,
    ItemPedidoEditar,
    KanbanAgrupadoResponse,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoComEndereco,
    PedidoResponseCompletoTotal,
    PedidoResponseSimplificado,
    PreviewCheckoutResponse,
    TipoPedidoCheckoutEnum,
)
from app.api.shared.schemas.schema_shared_enums import (
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
    PedidoStatusEnum,
    TipoEntregaEnum,
)
from app.api.cardapio.schemas.schema_transacao_pagamento import TransacaoStatusUpdateRequest
from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
from app.api.cardapio.services.pagamento.service_pagamento import PagamentoService
from app.api.cardapio.services.pagamento.service_pagamento_gateway import PaymentResult
from app.api.pedidos.services.service_pedido_helpers import (
    _dec,
    is_pix_online_meio_pagamento,
)
from app.api.pedidos.services.service_pedido_responses import PedidoResponseBuilder
from app.api.pedidos.utils.complementos import resolve_produto_complementos, resolve_complementos_diretos
from app.api.pedidos.services.service_pedido_taxas import TaxaService
from app.api.empresas.contracts.empresa_contract import IEmpresaContract
from app.api.cadastros.contracts.regiao_entrega_contract import IRegiaoEntregaContract
from app.api.catalogo.contracts.produto_contract import IProdutoContract, ProdutoEmpDTO
from app.api.catalogo.contracts.complemento_contract import IComplementoContract
from app.api.pedidos.services.service_pedido_kanban import KanbanService
# Migrado para modelos unificados - contratos não são mais necessários
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.chatbot.core.config_whatsapp import load_whatsapp_config
from app.api.chatbot.core.notifications import OrderNotification
from app.utils.logger import logger
from app.utils.database_utils import now_trimmed

from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.core import ProductCore
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter

if TYPE_CHECKING:
    from app.api.pedidos.schemas.schema_pedido_cliente import PedidoClienteListItem

QTD_MAX_ITENS = 200


class PedidoService:
    def __init__(
        self,
        db: Session,
        empresa_contract: IEmpresaContract | None = None,
        regiao_contract: IRegiaoEntregaContract | None = None,
        produto_contract: IProdutoContract | None = None,
        adicional_contract=None,
        complemento_contract: IComplementoContract | None = None,
        combo_contract=None,
    ):
        self.db = db
        self.repo = PedidoRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.repo_entregador = EntregadorRepository(db)
        self.pagamentos = PagamentoService(db)
        self.taxa_service = TaxaService(
            db,
            empresa_contract=empresa_contract,
            regiao_contract=regiao_contract,
        )
        self.produto_contract = produto_contract
        self.adicional_contract = adicional_contract
        self.complemento_contract = complemento_contract
        self.combo_contract = combo_contract
        
        # Inicializa ProductCore com os adapters
        # Se os contracts não foram fornecidos, cria os adapters
        produto_adapter = produto_contract if produto_contract else ProdutoAdapter(db)
        combo_adapter = combo_contract if combo_contract else ComboAdapter(db)
        complemento_adapter = complemento_contract if complemento_contract else ComplementoAdapter(db)
        
        self.product_core = ProductCore(
            produto_contract=produto_adapter,
            combo_contract=combo_adapter,
            complemento_contract=complemento_adapter,
        )
        self.response_builder = PedidoResponseBuilder()
        self.kanban_service = KanbanService(
            db,
            self.repo,
        )

    # ---------------- Helpers ---------------- 
    def _atualizar_status_pedido_por_pagamento(
        self,
        pedido: PedidoUnificadoModel,
        status_pagamento: PagamentoStatusEnum,
    ) -> bool:
        if not status_pagamento:
            return False

        status_atual = PedidoStatusEnum(pedido.status)
        novo_status = None
        motivo = None

        if status_pagamento == PagamentoStatusEnum.PAGO:
            if status_atual in {PedidoStatusEnum.A, PedidoStatusEnum.P, PedidoStatusEnum.I}:
                novo_status = PedidoStatusEnum.I.value
                motivo = "Pagamento confirmado"
        elif status_pagamento == PagamentoStatusEnum.AUTORIZADO:
            if status_atual == PedidoStatusEnum.A:
                novo_status = PedidoStatusEnum.I.value
                motivo = "Pagamento autorizado"
        elif status_pagamento in {PagamentoStatusEnum.CANCELADO, PagamentoStatusEnum.ESTORNADO}:
            if status_atual not in {PedidoStatusEnum.C, PedidoStatusEnum.E}:
                novo_status = PedidoStatusEnum.C.value
                motivo = "Pagamento cancelado"
        elif status_pagamento == PagamentoStatusEnum.RECUSADO:
            if status_atual not in {PedidoStatusEnum.C, PedidoStatusEnum.E}:
                novo_status = PedidoStatusEnum.A.value
                motivo = "Pagamento recusado"

        if novo_status and pedido.status != novo_status:
            self.repo.atualizar_status_pedido(pedido, novo_status, motivo=motivo)
            return True

        return False

    def _pedido_to_response(self, pedido: PedidoUnificadoModel) -> PedidoResponse:
        """Wrapper para manter compatibilidade com código existente."""
        return self.response_builder.pedido_to_response(pedido)

    def _calcular_taxas(
        self,
        *,
        tipo_entrega: TipoEntregaEnum,
        subtotal: Decimal,
        endereco=None,
        empresa_id: int | None = None,
    ) -> tuple[Decimal, Decimal, Optional[Decimal], Optional[int]]:
        """Wrapper para cálculo de taxas e distância."""
        return self.taxa_service.calcular_taxas(
            tipo_entrega=tipo_entrega,
            subtotal=subtotal,
            endereco=endereco,
            empresa_id=empresa_id,
        )

    @staticmethod
    def _status_descricao_delivery(status: PedidoStatusEnum | str) -> str:
        """Retorna descrição amigável para status de pedidos de delivery."""
        status_code = status.value if isinstance(status, PedidoStatusEnum) else str(status)
        mapa = {
            PedidoStatusEnum.P.value: "Pendente",
            PedidoStatusEnum.I.value: "Em impressão",
            PedidoStatusEnum.R.value: "Em preparo",
            PedidoStatusEnum.S.value: "Saiu para entrega",
            PedidoStatusEnum.E.value: "Entregue",
            PedidoStatusEnum.C.value: "Cancelado",
            PedidoStatusEnum.D.value: "Editado",
            PedidoStatusEnum.X.value: "Em edição",
            PedidoStatusEnum.A.value: "Aguardando pagamento",
        }
        return mapa.get(status_code, status_code)

    def _resolver_empresa_delivery(
        self,
        *,
        endereco,
        empresa_id: Optional[int],
        itens,
    ):
        if endereco is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Endereço é obrigatório para pedidos de delivery.",
            )

        empresa_preferida = None
        if empresa_id:
            empresa_preferida = self.repo_empresa.get_empresa_by_id(empresa_id)
            if not empresa_preferida:
                logger.warning(
                    "[Pedidos] Empresa informada no payload (%s) não foi encontrada. " 
                    "Será utilizada a empresa mais próxima.",
                    empresa_id,
                )
                empresa_preferida = None
            else:
                if not self.taxa_service.verificar_regioes_cadastradas(empresa_preferida.id):
                    logger.warning(
                        "[Pedidos] Empresa %s não possui faixas de entrega cadastradas. "
                        "Ignorando empresa informada no payload.",
                        empresa_preferida.id,
                    )
                    empresa_preferida = None
                elif not self._empresa_possui_produtos(empresa_preferida.id, itens):
                    logger.warning(
                        "[Pedidos] Empresa %s não possui todos os produtos do pedido. "
                        "Ignorando empresa informada no payload.",
                        empresa_preferida.id,
                    )
                    empresa_preferida = None

        empresa_encontrada, distancia = self._selecionar_empresa_mais_proxima(endereco, itens)
        if not empresa_encontrada:
            if empresa_preferida:
                # Mantém compatibilidade com comportamento anterior: se não foi possível
                # determinar a mais próxima (ex.: falta de coordenadas), usa empresa válida
                # informada no payload.
                return empresa_preferida, None
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Nenhuma empresa disponível para os itens e endereço informados.",
            )

        if empresa_preferida and empresa_preferida.id != empresa_encontrada.id:
            logger.info(
                "[Pedidos] Empresa %s informada no payload substituída pela mais próxima %s.",
                empresa_preferida.id,
                empresa_encontrada.id,
            )

        return empresa_encontrada, distancia

    def _selecionar_empresa_mais_proxima(self, endereco, itens):
        # Busca todas as empresas sem limite para garantir que encontra a mais próxima
        empresas = self.repo_empresa.list(skip=0, limit=None)
        if not empresas:
            return None, None

        # filtros: empresas com faixas ativas e todos os produtos disponíveis
        empresas_validas = []
        for empresa in empresas:
            if not self.taxa_service.verificar_regioes_cadastradas(empresa.id):
                continue
            if not self._empresa_possui_produtos(empresa.id, itens):
                continue
            empresas_validas.append(empresa)

        if not empresas_validas:
            return None, None

        # Obtém coordenadas do destino
        destino_coords_tuple = self.taxa_service.obter_coordenadas_endereco(endereco)
        if not destino_coords_tuple or destino_coords_tuple[0] is None or destino_coords_tuple[1] is None:
            return None, None
        
        from app.api.localizacao.models.coordenadas import Coordenadas
        destino_coords = Coordenadas.from_tuple(destino_coords_tuple)
        if destino_coords is None:
            return None, None

        melhor_empresa = None
        menor_distancia = None
        for empresa in empresas_validas:
            origem_coords_tuple = self.taxa_service.obter_coordenadas_empresa(empresa.id)
            if not origem_coords_tuple or origem_coords_tuple[0] is None or origem_coords_tuple[1] is None:
                continue

            origem_coords = Coordenadas.from_tuple(origem_coords_tuple)
            if origem_coords is None:
                continue

            distancia = self.taxa_service.geo_service.calcular_distancia(
                origem_coords,
                destino_coords,
            )
            if distancia is None:
                continue

            # Aqui a lógica é apenas escolher a empresa mais próxima.
            # A validação da faixa de entrega e cálculo da taxa são feitos depois,
            # em TaxaService.calcular_taxas, já com a empresa escolhida.
            if menor_distancia is None or distancia < menor_distancia:
                menor_distancia = distancia
                melhor_empresa = empresa

        return melhor_empresa, menor_distancia

    def _empresa_possui_produtos(self, empresa_id: int, itens) -> bool:
        for item in itens or []:
            codigo = getattr(item, "produto_cod_barras", None)
            if not codigo:
                return False
            if self.produto_contract is not None:
                pe_dto: ProdutoEmpDTO | None = self.produto_contract.obter_produto_emp_por_cod(empresa_id, codigo)
                if not pe_dto or not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                    return False
            else:
                produto = self.repo.get_produto_emp(empresa_id, codigo)
                if not produto or not produto.produto or not produto.disponivel or not produto.produto.ativo:
                    return False#
        return True

    def _aplicar_cupom(
        self,
        *,
        cupom_id: Optional[int],
        subtotal: Decimal,
        empresa_id: int,
    ) -> Decimal:
        """Wrapper para manter compatibilidade com código existente."""
        return self.taxa_service.aplicar_cupom(
            cupom_id=cupom_id,
            subtotal=subtotal,
            empresa_id=empresa_id,
            repo=self.repo,
        )

    def _deve_usar_gateway(self, metodo: PagamentoMetodoEnum) -> bool:
        """Determina se o método de pagamento deve usar o gateway de pagamento."""
        return metodo == PagamentoMetodoEnum.PIX_ONLINE

    def verificar_endereco_em_uso(self, endereco_id: int) -> bool:
        """Verifica se um endereço está sendo usado em pedidos ativos (não cancelados/entregues)."""
        pedidos_ativos = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.endereco_id == endereco_id,
                PedidoUnificadoModel.status.in_(["P", "I", "R", "S", "D"])
            )
            .count()
        )
        return pedidos_ativos > 0

    def get_pedidos_por_regiao(self, latitude_centro: float, longitude_centro: float, raio_km: float = 5.0):
        """Retorna pedidos dentro de uma região geográfica específica usando PostGIS."""
        ponto_centro = f"ST_GeomFromText('POINT({longitude_centro} {latitude_centro})', 4326)"
        raio_metros = raio_km * 1000
        
        query = text(f"""
            SELECT p.*, 
                   ST_Distance(p.endereco_geo, {ponto_centro}) as distancia_metros
            FROM pedidos.pedidos p
            WHERE p.endereco_geo IS NOT NULL
              AND p.tipo_entrega = 'DELIVERY'
              AND ST_DWithin(p.endereco_geo, {ponto_centro}, :raio_metros)
            ORDER BY distancia_metros
        """)
        
        result = self.db.execute(query, {"raio_metros": raio_metros})
        
        pedidos_na_regiao = []
        for row in result:
            pedido = (
                self.db.query(PedidoUnificadoModel)
                .filter(
                    PedidoUnificadoModel.id == row.id,
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value
                )
                .first()
            )
            if pedido:
                pedidos_na_regiao.append({
                    "pedido": pedido,
                    "distancia_km": row.distancia_metros / 1000
                })
        
        return pedidos_na_regiao

    def get_pedidos_por_poligono(self, coordenadas_poligono: list):
        """Retorna pedidos dentro de um polígono específico."""
        coords_str = ", ".join([f"{lon} {lat}" for lon, lat in coordenadas_poligono])
        poligono_wkt = f"POLYGON(({coords_str}))"
        
        query = text("""
            SELECT p.*
            FROM pedidos.pedidos p
            WHERE p.endereco_geo IS NOT NULL
              AND p.tipo_entrega = 'DELIVERY'
              AND ST_Within(p.endereco_geo, ST_GeomFromText(:poligono, 4326))
        """)
        
        result = self.db.execute(query, {"poligono": poligono_wkt})
        
        pedidos = []
        for row in result:
            pedido = (
                self.db.query(PedidoUnificadoModel)
                .filter(
                    PedidoUnificadoModel.id == row.id,
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value
                )
                .first()
            )
            if pedido:
                pedidos.append(pedido)
        
        return pedidos

    def _recalcular_pedido(self, pedido: PedidoUnificadoModel):
        """Recalcula subtotal, desconto, taxas e valor total do pedido e salva no banco."""
        subtotal = self.db.query(
            func.sum(PedidoItemUnificadoModel.quantidade * PedidoItemUnificadoModel.preco_unitario)
        ).filter(PedidoItemUnificadoModel.pedido_id == pedido.id).scalar() or Decimal("0")

        subtotal = Decimal(subtotal)
        desconto = self._aplicar_cupom(
            cupom_id=pedido.cupom_id,
            subtotal=subtotal,
            empresa_id=pedido.empresa_id,
        )

        endereco = pedido.endereco
        taxa_entrega, taxa_servico, distancia_km, _ = self._calcular_taxas(
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
            distancia_km=distancia_km,
        )
        self.repo.commit()
        self.db.refresh(pedido)

    # ---------------- Fluxos ----------------
    async def finalizar_pedido(self, payload: FinalizarPedidoRequest, cliente_id: int) -> PedidoResponse:
        # Suporta tanto o formato novo (payload.produtos.*) quanto o legado (itens/receitas/combos na raiz)
        produtos_payload = getattr(payload, "produtos", None)
        if produtos_payload is not None:
            itens_normais = produtos_payload.itens or []
            receitas_req = getattr(produtos_payload, "receitas", None) or []
            combos_req = getattr(produtos_payload, "combos", None) or []
        else:
            itens_normais = payload.itens or []
            receitas_req = getattr(payload, "receitas", None) or []
            combos_req = getattr(payload, "combos", None) or []

        if not itens_normais and not receitas_req and not combos_req:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if (len(itens_normais) + len(receitas_req)) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        meios_pagamento_list = []
        meio_pagamento = None
        
        if payload.meios_pagamento and len(payload.meios_pagamento) > 0:
            for mp in payload.meios_pagamento:
                # Suporta tanto mp.id (novo) quanto mp.meio_pagamento_id (legado)
                mp_id = getattr(mp, "id", None) or getattr(mp, "meio_pagamento_id", None)
                if mp_id is None:
                    raise HTTPException(400, "ID do meio de pagamento é obrigatório em 'meios_pagamento'.")
                mp_obj = MeioPagamentoService(self.db).get(mp_id)
                if not mp_obj or not mp_obj.ativo:
                    raise HTTPException(400, f"Meio de pagamento {mp_id} inválido ou inativo")
                meios_pagamento_list.append({
                    'meio_pagamento': mp_obj,
                    'valor': mp.valor
                })
            # Para compatibilidade, considera o primeiro meio de pagamento como principal
            meio_pagamento = meios_pagamento_list[0]['meio_pagamento']

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
            
            endereco_latitude = float(endereco.latitude) if endereco.latitude else None
            endereco_longitude = float(endereco.longitude) if endereco.longitude else None
            
            if endereco_latitude and endereco_longitude:
                from geoalchemy2 import WKTElement
                endereco_geo = WKTElement(f'POINT({endereco_longitude} {endereco_latitude})', srid=4326)
            
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
            status_inicial = PedidoStatusEnum.I.value

            empresa = None
            empresa_id = payload.empresa_id
            if payload.tipo_entrega == TipoEntregaEnum.DELIVERY:
                empresa, _ = self._resolver_empresa_delivery(
                    endereco=endereco,
                    empresa_id=empresa_id,
                    itens=itens_normais,
                )
                empresa_id = empresa.id
                payload.empresa_id = empresa_id
            else:
                if not empresa_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empresa é obrigatória para este tipo de pedido.")
                empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
                if not empresa:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

            pedido = self.repo.criar_pedido(
                cliente_id=cliente.id,
                empresa_id=empresa_id,
                endereco_id=payload.endereco_id,
                meio_pagamento_id=getattr(meio_pagamento, "id", None) if meio_pagamento is not None else None,
                status=status_inicial,
                tipo_entrega=payload.tipo_entrega.value if hasattr(payload.tipo_entrega, "value") else payload.tipo_entrega,
                origem=payload.origem.value if hasattr(payload.origem, "value") else payload.origem,
                endereco_snapshot=endereco_snapshot,
                endereco_geo=endereco_geo,
            )

            logger.info(f"[finalizar_pedido] criado pedido_id={pedido.id} cliente_id={pedido.cliente_id}")

            subtotal = Decimal("0")

            # Itens normais (produtos com código de barras)
            for it in itens_normais:
                if self.produto_contract is not None:
                    pe_dto = self.produto_contract.obter_produto_emp_por_cod(empresa_id, it.produto_cod_barras)
                    if not pe_dto:
                        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
                    if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")

                    preco = _dec(pe_dto.preco_venda)
                    subtotal += preco * it.quantidade
                    self.repo.adicionar_item(
                        pedido_id=pedido.id,
                        cod_barras=it.produto_cod_barras,
                        quantidade=it.quantidade,
                        preco_unitario=preco,
                        observacao=self._montar_observacao_item(it),
                        produto_descricao_snapshot=(pe_dto.produto.descricao if pe_dto.produto else None),
                        produto_imagem_snapshot=None,
                        complementos=getattr(it, "complementos", None),
                    )
                else:
                    pe = self.repo.get_produto_emp(empresa_id, it.produto_cod_barras)
                    if not pe:
                        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
                    if not pe.disponivel or not (pe.produto and pe.produto.ativo):
                        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")

                    preco = _dec(pe.preco_venda)
                    subtotal += preco * it.quantidade
                    self.repo.adicionar_item(
                        pedido_id=pedido.id,
                        cod_barras=it.produto_cod_barras,
                        quantidade=it.quantidade,
                        preco_unitario=preco,
                        observacao=self._montar_observacao_item(it),
                        produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                        produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
                        complementos=getattr(it, "complementos", None),
                    )

                adicionais_total, _ = self._resolver_adicionais_item_snapshot(it)
                subtotal += adicionais_total

            # Receitas (sem produto_cod_barras no payload, usam apenas receita_id)
            for rec in receitas_req:
                qtd_rec = max(int(getattr(rec, "quantidade", 1) or 1), 1)
                
                # Busca receita do banco
                receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == rec.receita_id).first()
                
                # Usa ProductCore para buscar e validar
                product = self.product_core.buscar_receita(
                    receita_id=rec.receita_id,
                    empresa_id=empresa_id,
                    receita_model=receita_model,
                )
                
                if not product:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Receita {rec.receita_id} não encontrada ou inativa",
                    )
                
                if not self.product_core.validar_disponivel(product, qtd_rec):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"Receita {rec.receita_id} não disponível",
                    )
                
                if not self.product_core.validar_empresa(product, empresa_id):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"Receita {rec.receita_id} não pertence à empresa {empresa_id}",
                    )

                # Calcula preço com complementos usando ProductCore
                complementos_rec = getattr(rec, "complementos", None) or []
                preco_total_rec, _ = self.product_core.calcular_preco_com_complementos(
                    product=product,
                    quantidade=qtd_rec,
                    complementos_request=complementos_rec,
                )
                subtotal += preco_total_rec

                # Cria item de receita no banco
                preco_unit_rec = preco_total_rec / qtd_rec
                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    receita_id=rec.receita_id,
                    quantidade=qtd_rec,
                    preco_unitario=preco_unit_rec,
                    observacao=self._montar_observacao_item(rec) if hasattr(rec, 'observacao') else None,
                    produto_descricao_snapshot=product.nome or product.descricao,
                    complementos=complementos_rec,
                )

            # Combos opcionais: adiciona ao subtotal, cria item de combo e aplica adicionais de combo (se existirem)
            for cb in combos_req or []:
                qtd_combo = max(int(getattr(cb, "quantidade", 1) or 1), 1)
                
                # Usa ProductCore para buscar e validar
                product = self.product_core.buscar_combo(cb.combo_id)
                
                if not product:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Combo {cb.combo_id} não encontrado ou inativo")
                
                if not self.product_core.validar_disponivel(product, qtd_combo):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"Combo {cb.combo_id} não disponível",
                    )
                
                if not self.product_core.validar_empresa(product, empresa_id):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"Combo {cb.combo_id} não pertence à empresa {empresa_id}",
                    )

                # Calcula preço com complementos usando ProductCore
                complementos_combo = getattr(cb, "complementos", None) or []
                preco_total_combo, _ = self.product_core.calcular_preco_com_complementos(
                    product=product,
                    quantidade=qtd_combo,
                    complementos_request=complementos_combo,
                )
                subtotal += preco_total_combo

                # Cria item de combo no banco (um item por combo, não itens individuais)
                preco_unit_combo = preco_total_combo / qtd_combo
                observacao_combo = f"Combo #{product.identifier} - {product.nome}"
                if hasattr(cb, 'observacao') and cb.observacao:
                    observacao_combo += f" | {cb.observacao}"
                
                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    combo_id=cb.combo_id,
                    quantidade=qtd_combo,
                    preco_unitario=preco_unit_combo,
                    observacao=observacao_combo,
                    produto_descricao_snapshot=product.nome or product.descricao,
                    complementos=complementos_combo,
                )
            desconto = self._aplicar_cupom(
                cupom_id=payload.cupom_id,
                subtotal=subtotal,
                empresa_id=empresa_id,
            )
            taxa_entrega, taxa_servico, distancia_km, _ = self._calcular_taxas(
                tipo_entrega=payload.tipo_entrega if isinstance(payload.tipo_entrega, TipoEntregaEnum)
                            else TipoEntregaEnum(payload.tipo_entrega),
                subtotal=subtotal,
                endereco=endereco,
                empresa_id=empresa_id,
            )

            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
                distancia_km=distancia_km,
            )

            pedido.observacao_geral = payload.observacao_geral
            if payload.troco_para:
                pedido.troco_para = _dec(payload.troco_para)

            valor_total = _dec(pedido.valor_total or 0)
            
            if meios_pagamento_list:
                soma_pagamentos = sum(_dec(mp['valor']) for mp in meios_pagamento_list)
                if soma_pagamentos < valor_total:
                    # Ajusta automaticamente o valor do pagamento para o valor total do pedido
                    # Isso evita erros quando o frontend/chatbot calcula incorretamente
                    diferenca = valor_total - soma_pagamentos
                    logger.warning(
                        f"[finalizar_pedido] Ajustando valor do pagamento: "
                        f"soma_pagamentos={float(soma_pagamentos)}, valor_total={float(valor_total)}, "
                        f"diferenca={float(diferenca)}"
                    )
                    # Ajusta o primeiro meio de pagamento para cobrir a diferença
                    if len(meios_pagamento_list) > 0:
                        meios_pagamento_list[0]['valor'] = float(valor_total)
                        logger.info(
                            f"[finalizar_pedido] Valor ajustado para {float(valor_total)} no primeiro meio de pagamento"
                        )
            
            if getattr(payload, "troco_para", None) is not None and meio_pagamento is not None:
                mp_tipo = getattr(meio_pagamento, "tipo", None)
                is_dinheiro = (
                    mp_tipo == MeioPagamentoTipoEnum.DINHEIRO
                    or str(mp_tipo).upper() == "DINHEIRO"
                )
                if is_dinheiro:
                    troco_para = _dec(payload.troco_para)
                    if troco_para < valor_total:
                        raise HTTPException(
                            status.HTTP_400_BAD_REQUEST,
                            detail={
                                "code": "TROCO_INSUFICIENTE",
                                "message": "Valor para troco menor que o total do pedido.",
                                "valor_total": float(valor_total),
                                "troco_para": float(troco_para),
                            },
                        )

            logger.info(f"[finalizar_pedido] antes commit cliente_id={pedido.cliente_id}")
            self.repo.commit()
            logger.info(f"[finalizar_pedido] após commit cliente_id={pedido.cliente_id}")
            
            if meios_pagamento_list:
                from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
                pagamento_repo = PagamentoRepository(self.db)
                
                for mp_data in meios_pagamento_list:
                    mp_obj = mp_data['meio_pagamento']
                    valor_parcial = _dec(mp_data['valor'])
                    
                    metodo = None
                    gateway = None
                    
                    if mp_obj.tipo == MeioPagamentoTipoEnum.PIX_ONLINE or str(mp_obj.tipo) == "PIX_ONLINE":
                        metodo = PagamentoMetodoEnum.PIX_ONLINE
                        gateway = PagamentoGatewayEnum.MERCADOPAGO
                    elif mp_obj.tipo == MeioPagamentoTipoEnum.PIX_ENTREGA or str(mp_obj.tipo) == "PIX_ENTREGA":
                        metodo = PagamentoMetodoEnum.PIX
                        gateway = PagamentoGatewayEnum.PIX_INTERNO
                    elif mp_obj.tipo == MeioPagamentoTipoEnum.OUTROS or str(mp_obj.tipo) == "OUTROS":
                        metodo = PagamentoMetodoEnum.OUTRO
                        gateway = PagamentoGatewayEnum.PIX_INTERNO
                    elif mp_obj.tipo == MeioPagamentoTipoEnum.CARTAO_ENTREGA or str(mp_obj.tipo) == "CARTAO_ENTREGA":
                        metodo = PagamentoMetodoEnum.CREDITO
                        gateway = PagamentoGatewayEnum.PIX_INTERNO
                    elif mp_obj.tipo == MeioPagamentoTipoEnum.DINHEIRO or str(mp_obj.tipo) == "DINHEIRO":
                        metodo = PagamentoMetodoEnum.DINHEIRO
                        gateway = PagamentoGatewayEnum.PIX_INTERNO
                    else:
                        metodo = PagamentoMetodoEnum.OUTRO
                        gateway = PagamentoGatewayEnum.PIX_INTERNO
                    
                    transacao = pagamento_repo.criar(
                        pedido_id=pedido.id,
                        meio_pagamento_id=mp_obj.id,
                        gateway=gateway.value,
                        metodo=metodo.value,
                        valor=valor_parcial,
                        status="PAGO" if not is_pix_online_meio_pagamento(mp_obj) else "PENDENTE",
                        provider_transaction_id=f"direct_{pedido.id}_{metodo.value}_{len(meios_pagamento_list)}" if not is_pix_online_meio_pagamento(mp_obj) else None
                    )
                    
                    if is_pix_online_meio_pagamento(mp_obj):
                        try:
                            await self.pagamentos.iniciar_transacao(
                                pedido_id=pedido.id,
                                meio_pagamento_id=mp_obj.id,
                                valor=valor_parcial,
                                metodo=metodo,
                                gateway=gateway,
                                metadata={"pedido_id": pedido.id, "empresa_id": pedido.empresa_id},
                            )
                        except Exception as e:
                            logger.error(f"Erro ao iniciar transação PIX_ONLINE: {e}")
                
                self.repo.commit()

            pedido = self.repo.get_pedido(pedido.id)
            logger.info(f"[finalizar_pedido] get_pedido cliente_id={pedido.cliente_id if pedido else None}")

        except HTTPException:
            logger.exception("[finalizar_pedido] HTTPException - rollback acionado")
            self.repo.rollback()
            raise
        except Exception as e:
            logger.exception("[finalizar_pedido] Exception inesperada - rollback acionado: %s", e)
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao finalizar pedido: {e}")

        # Notifica novo pedido em background
        try:
            import asyncio
            from app.api.pedidos.utils.pedido_notification_helper import notificar_novo_pedido
            # Recarrega pedido com todos os relacionamentos para a notificação
            pedido_completo = self.repo.get_pedido(pedido.id)
            if pedido_completo:
                asyncio.create_task(notificar_novo_pedido(pedido_completo))
        except Exception as e:
            # Loga erro mas não quebra o fluxo
            logger.error(f"Erro ao agendar notificação de novo pedido {pedido.id}: {e}")

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

        if pedido.transacao and pedido.transacao.status in ("PAGO", "AUTORIZADO"):
            return self._pedido_to_response(pedido)

        if gateway is None:
            if self._deve_usar_gateway(metodo):
                gateway = PagamentoGatewayEnum.PIX_INTERNO
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

            if self._deve_usar_gateway(metodo):
                result = await self.pagamentos.gateway.charge(
                    order_id=pedido.id,
                    amount=_dec(pedido.valor_total),
                    metodo=metodo,
                    gateway=gateway,
                    metadata={"empresa_id": pedido.empresa_id},
                )
            else:
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
                self._atualizar_status_pedido_por_pagamento(pedido, result.status)
            else:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="RECUSADO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                )
                self._atualizar_status_pedido_por_pagamento(pedido, PagamentoStatusEnum.RECUSADO)

            self.repo.commit()
            pedido = self.repo.get_pedido(pedido.id)
            return self._pedido_to_response(pedido)

        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao confirmar pagamento: {e}")

    async def atualizar_status_pagamento(
        self,
        *,
        pedido_id: int,
        payload: TransacaoStatusUpdateRequest,
    ) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        transacao = await self.pagamentos.atualizar_status(
            pedido_id=pedido_id,
            payload=payload,
        )

        pedido = self.repo.get_pedido(pedido_id)
        mudou_status = self._atualizar_status_pedido_por_pagamento(pedido, transacao.status)

        if mudou_status:
            self.repo.commit()
            pedido = self.repo.get_pedido(pedido_id)

        return self._pedido_to_response(pedido)

    # --------------- Consultas ---------------
    def listar_pedidos(self, cliente_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponse]:
        pedidos = (
            self.repo.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.cliente_id == cliente_id
            )
            .order_by(PedidoUnificadoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [self._pedido_to_response(p) for p in pedidos]

    def listar_pedidos_cliente_unificado(
        self,
        cliente_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list["PedidoClienteListItem"]:
        """Lista pedidos do cliente incluindo delivery, mesa e balcão."""
        from app.api.pedidos.schemas.schema_pedido_cliente import PedidoClienteListItem
        from app.api.pedidos.services.service_pedidos_mesa import PedidoMesaService
        from app.api.pedidos.services.service_pedidos_balcao import PedidoBalcaoService

        if limit is None or limit <= 0:
            limit = 50

        consulta_limite = skip + limit

        pedidos_delivery = self.listar_pedidos_completo(
            cliente_id=cliente_id,
            skip=0,
            limit=consulta_limite,
        )

        itens: list[PedidoClienteListItem] = []
        for pedido in pedidos_delivery:
            itens.append(
                PedidoClienteListItem(
                    tipo_pedido=TipoPedidoCheckoutEnum.DELIVERY,
                    criado_em=pedido.data_criacao,
                    atualizado_em=pedido.data_atualizacao,
                    status_codigo=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    status_descricao=self._status_descricao_delivery(pedido.status),
                    numero_pedido=str(pedido.id),
                    valor_total=pedido.valor_total,
                    delivery=pedido,
                )
            )

        mesa_service = PedidoMesaService(self.db, complemento_contract=None)
        pedidos_mesa = mesa_service.list_pedidos_by_cliente(
            cliente_id=cliente_id,
            empresa_id=None,
            skip=0,
            limit=consulta_limite,
        )
        for pedido in pedidos_mesa:
            status_value = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
            itens.append(
                PedidoClienteListItem(
                    tipo_pedido=TipoPedidoCheckoutEnum.MESA,
                    criado_em=pedido.data_criacao,
                    atualizado_em=pedido.data_atualizacao,
                    status_codigo=status_value,
                    status_descricao=self._status_descricao_delivery(pedido.status),
                    numero_pedido=str(pedido.id),
                    valor_total=pedido.valor_total,
                    mesa=pedido,
                )
            )

        balcao_service = PedidoBalcaoService(self.db, complemento_contract=None)
        pedidos_balcao = balcao_service.list_pedidos_by_cliente(
            cliente_id=cliente_id,
            skip=0,
            limit=consulta_limite,
        )
        for pedido in pedidos_balcao:
            status_value = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
            itens.append(
                PedidoClienteListItem(
                    tipo_pedido=TipoPedidoCheckoutEnum.BALCAO,
                    criado_em=pedido.data_criacao,
                    atualizado_em=pedido.data_atualizacao,
                    status_codigo=status_value,
                    status_descricao=self._status_descricao_delivery(pedido.status),
                    numero_pedido=str(pedido.id),
                    valor_total=pedido.valor_total,
                    balcao=pedido,
                )
            )

        itens.sort(key=lambda item: item.criado_em, reverse=True)
        limite_superior = skip + limit
        return itens[skip:limite_superior]

    def listar_pedidos_completo(self, cliente_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponseSimplificado]:
        """Lista pedidos com dados simplificados incluindo nome do meio de pagamento"""
        from sqlalchemy.orm import selectinload
        from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        pedidos = (
            self.repo.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.meio_pagamento),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais)
            )
            .filter(
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.cliente_id == cliente_id
            )
            .order_by(PedidoUnificadoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        # ⚠️ NUNCA mutar `pedido.itens` aqui: o relacionamento tem `delete-orphan` e isso pode deletar itens no commit do get_db().
        return [self.response_builder.pedido_to_response_simplificado(p) for p in pedidos]

    def get_pedido_by_id(self, pedido_id: int) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response(pedido)

    def get_pedido_by_id_completo(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self.response_builder.pedido_to_response_completo(pedido)

    def get_pedido_by_id_completo_com_endereco(self, pedido_id: int) -> PedidoResponseCompletoComEndereco:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self.response_builder.pedido_to_response_completo_com_endereco(pedido)

    def get_pedido_by_id_completo_total(self, pedido_id: int) -> PedidoResponseCompletoTotal:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self.response_builder.pedido_to_response_completo_total(pedido)

    # ---------------- Admin / Kanban ----------------
    def list_all_kanban(
        self, 
        date_filter: date, 
        empresa_id: int = 1, 
        limit: int = 500,
        tipo: Optional[TipoEntregaEnum] = None,
    ) -> KanbanAgrupadoResponse:
        """Lista todos os pedidos para visualização no Kanban, agrupados por categoria."""
        return self.kanban_service.list_all_kanban(
            date_filter=date_filter, 
            empresa_id=empresa_id, 
            limit=limit,
            tipo=tipo,
        )

    # ---------------- Atualizações ----------------
    def atualizar_status(self, pedido_id: int, novo_status: PedidoStatusEnum, user_id: int | None = None) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        # Impede setar status E (Entregue) para pedidos de delivery
        # Delivery deve usar o endpoint fechar-conta para marcar como pago
        if novo_status == PedidoStatusEnum.E:
            if pedido.is_delivery() or pedido.is_retirada():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não é possível setar status 'Entregue' para pedidos de delivery/retirada. Use o endpoint 'fechar-conta' para marcar o pedido como pago."
                )

        observacoes = None
        if novo_status == PedidoStatusEnum.E:
            obs_parts = []
            if pedido.cliente:
                obs_parts.append(f"Cliente: {pedido.cliente.nome}")
            if pedido.valor_total:
                obs_parts.append(f"R$ {pedido.valor_total:.2f}")
            if pedido.entregador_id and pedido.entregador:
                obs_parts.append(f"Entregador: {pedido.entregador.nome}")
            
            observacoes = " | ".join(obs_parts) if obs_parts else None
        
        self.repo.atualizar_status_pedido(
            pedido=pedido,
            novo_status=novo_status.value,
            observacoes=observacoes,
            criado_por_id=user_id,
        )
        
        self.db.commit()
        self.db.refresh(pedido)
        if novo_status == PedidoStatusEnum.S and pedido.entregador_id:
            self._notificar_entregador_rotas(pedido)
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
            meio_pagamento_atual = None
            try:
                meio_pagamento_id_ref = payload.meio_pagamento_id if payload.meio_pagamento_id is not None else pedido.meio_pagamento_id
                if meio_pagamento_id_ref is not None:
                    meio_pagamento_atual = MeioPagamentoService(self.db).get(meio_pagamento_id_ref)
            except Exception:
                meio_pagamento_atual = None

            pedido.troco_para = _dec(payload.troco_para)

            subtotal = pedido.subtotal or Decimal("0")
            desconto = self._aplicar_cupom(
                cupom_id=pedido.cupom_id,
                subtotal=subtotal,
                empresa_id=pedido.empresa_id,
            )
            taxa_entrega, taxa_servico, distancia_km, _ = self._calcular_taxas(
                tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                            else TipoEntregaEnum(pedido.tipo_entrega),
                subtotal=subtotal,
                endereco=endereco or pedido.endereco,
                empresa_id=pedido.empresa_id,
            )
            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
                distancia_km=distancia_km,
            )

            if meio_pagamento_atual is not None:
                mp_tipo = getattr(meio_pagamento_atual, "tipo", None)
                is_dinheiro = (
                    mp_tipo == MeioPagamentoTipoEnum.DINHEIRO
                    or str(mp_tipo).upper() == "DINHEIRO"
                )
                if is_dinheiro:
                    valor_total = _dec(pedido.valor_total or 0)
                    troco_para = _dec(pedido.troco_para)
                    if troco_para < valor_total:
                        raise HTTPException(
                            status.HTTP_400_BAD_REQUEST,
                            detail={
                                "code": "TROCO_INSUFICIENTE",
                                "message": "Valor para troco menor que o total do pedido.",
                                "valor_total": float(valor_total),
                                "troco_para": float(troco_para),
                            },
                        )

        subtotal = pedido.subtotal or Decimal("0")
        desconto = self._aplicar_cupom(
            cupom_id=pedido.cupom_id,
            subtotal=subtotal,
            empresa_id=pedido.empresa_id,
        )
        taxa_entrega, taxa_servico, distancia_km, _ = self._calcular_taxas(
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            subtotal=subtotal,
            endereco=endereco or pedido.endereco,
            empresa_id=pedido.empresa_id,
        )
        self.repo.atualizar_totais(
            pedido,
            subtotal=subtotal,
            desconto=desconto,
            taxa_entrega=taxa_entrega,
            taxa_servico=taxa_servico,
            distancia_km=distancia_km,
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

            if self.produto_contract is not None:
                pe_dto = self.produto_contract.obter_produto_emp_por_cod(pedido.empresa_id, item.produto_cod_barras)
                if not pe_dto:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {item.produto_cod_barras} não encontrado")
                if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {item.produto_cod_barras}")

                preco = _dec(pe_dto.preco_venda)
                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    cod_barras=item.produto_cod_barras,
                    quantidade=item.quantidade,
                    preco_unitario=preco,
                    observacao=item.observacao,
                    produto_descricao_snapshot=(pe_dto.produto.descricao if pe_dto.produto else None),
                    produto_imagem_snapshot=None,
                )
            else:
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
        """Vincula ou desvincula um entregador a um pedido de delivery."""
        # Verifica se o pedido existe
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Se entregador_id for None, apenas desvincula
        if entregador_id is None:
            pedido.entregador_id = None
            self.db.commit()
            self.db.refresh(pedido)
            logger.info(f"[vincular_entregador] Entregador desvinculado do pedido {pedido_id}")
            return self._pedido_to_response(pedido)

        # Valida se o entregador existe
        entregador_repo = EntregadorRepository(self.db)
        entregador = entregador_repo.get(entregador_id)
        if not entregador:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Entregador com ID {entregador_id} não encontrado"
            )

        # Valida se o entregador está vinculado à empresa do pedido
        # Carrega o relacionamento de empresas explicitamente
        entregador_com_empresas = (
            self.db.query(EntregadorDeliveryModel)
            .options(joinedload(EntregadorDeliveryModel.empresas))
            .filter(EntregadorDeliveryModel.id == entregador_id)
            .first()
        )
        
        if not entregador_com_empresas:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Entregador com ID {entregador_id} não encontrado"
            )

        empresa_ids = [emp.id for emp in entregador_com_empresas.empresas] if entregador_com_empresas.empresas else []
        if pedido.empresa_id not in empresa_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Entregador {entregador_id} não está vinculado à empresa {pedido.empresa_id} do pedido"
            )

        # Vincula o entregador
        try:
            pedido.entregador_id = entregador_id
            self.db.commit()
            self.db.refresh(pedido)
            logger.info(f"[vincular_entregador] Entregador {entregador_id} vinculado ao pedido {pedido_id}")
            if self._status_value(pedido.status) == PedidoStatusEnum.S.value:
                self._notificar_entregador_rotas(pedido)
            return self._pedido_to_response(pedido)
        except Exception as exc:
            self.db.rollback()
            logger.error(f"[vincular_entregador] Falha inesperada: {exc}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao vincular entregador: {str(exc)}")

    def desvincular_entregador(self, pedido_id: int) -> PedidoResponse:
        """Desvincula o entregador atual de um pedido (idempotente)."""
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Se já não tem entregador, retorna sucesso (idempotente)
        if not pedido.entregador_id:
            logger.info(f"[desvincular_entregador] Pedido {pedido_id} já não possui entregador vinculado")
            return self._pedido_to_response(pedido)

        pedido.entregador_id = None
        self.db.commit()
        self.db.refresh(pedido)

        logger.info(f"[desvincular_entregador] Entregador desvinculado do pedido {pedido_id}")
        
        return self._pedido_to_response(pedido)

    @staticmethod
    def _status_value(status: StatusPedido | PedidoStatusEnum | str) -> str:
        if isinstance(status, (StatusPedido, PedidoStatusEnum)):
            return status.value
        return str(status)

    @staticmethod
    def _whatsapp_config_valida(empresa_id: Optional[str] = None) -> bool:
        required_keys = ("access_token", "phone_number_id", "api_version")
        cfg = load_whatsapp_config(str(empresa_id) if empresa_id is not None else None)
        return all(cfg.get(chave) for chave in required_keys)

    def _execute_async(self, coro_factory: Callable[[], object]) -> object:
        primary_coro = coro_factory()
        try:
            return asyncio.run(primary_coro) if asyncio.iscoroutine(primary_coro) else primary_coro
        except RuntimeError:
            if asyncio.iscoroutine(primary_coro):
                primary_coro.close()
            result_container: dict[str, object] = {}
            error_container: dict[str, BaseException] = {}

            def _runner():
                try:
                    followup_coro = coro_factory()
                    if asyncio.iscoroutine(followup_coro):
                        result_container["result"] = asyncio.run(followup_coro)
                    else:
                        result_container["result"] = followup_coro
                except BaseException as exc:  # noqa: BLE001
                    error_container["error"] = exc

            thread = threading.Thread(target=_runner, daemon=True)
            thread.start()
            thread.join()

            if "error" in error_container:
                raise error_container["error"]
            return result_container.get("result")

    @staticmethod
    def _extract_endereco_snapshot(pedido: PedidoUnificadoModel) -> dict[str, object]:
        snapshot = pedido.endereco_snapshot if isinstance(pedido.endereco_snapshot, dict) else None
        if snapshot:
            return snapshot
        endereco = getattr(pedido, "endereco", None)
        if not endereco:
            return {}
        return {
            "logradouro": getattr(endereco, "logradouro", None),
            "numero": getattr(endereco, "numero", None),
            "complemento": getattr(endereco, "complemento", None),
            "bairro": getattr(endereco, "bairro", None),
            "cidade": getattr(endereco, "cidade", None),
            "estado": getattr(endereco, "estado", None),
            "cep": getattr(endereco, "cep", None),
            "latitude": float(endereco.latitude) if getattr(endereco, "latitude", None) is not None else None,
            "longitude": float(endereco.longitude) if getattr(endereco, "longitude", None) is not None else None,
        }

    @staticmethod
    def _format_endereco_snapshot(snapshot: dict[str, object]) -> str:
        if not snapshot:
            return ""
        partes: list[str] = []
        logradouro = snapshot.get("logradouro")
        numero = snapshot.get("numero")
        if logradouro:
            logradouro_str = str(logradouro)
            if numero:
                logradouro_str = f"{logradouro_str}, {numero}"
            partes.append(logradouro_str)
        complemento = snapshot.get("complemento")
        if complemento:
            partes.append(str(complemento))
        bairro = snapshot.get("bairro")
        if bairro:
            partes.append(str(bairro))
        cidade = snapshot.get("cidade")
        estado = snapshot.get("estado")
        cidade_estado = ", ".join(str(valor) for valor in [cidade, estado] if valor)
        if cidade_estado:
            partes.append(cidade_estado)
        cep = snapshot.get("cep")
        if cep:
            partes.append(str(cep))
        return " - ".join(partes)

    def _build_google_maps_link(self, pedidos: list[PedidoUnificadoModel]) -> str | None:
        addresses: list[str] = []
        for pedido in pedidos:
            snapshot = self._extract_endereco_snapshot(pedido)
            lat = snapshot.get("latitude")
            lon = snapshot.get("longitude")
            coordinate = None
            if lat is not None and lon is not None:
                try:
                    coordinate = f"{float(lat):.6f},{float(lon):.6f}"
                except (TypeError, ValueError):
                    coordinate = None
            if coordinate:
                addresses.append(coordinate)
            else:
                formatted = self._format_endereco_snapshot(snapshot)
                if formatted:
                    addresses.append(formatted)

        if not addresses:
            return None

        base_url = "https://www.google.com/maps/dir/?api=1&travelmode=driving"
        if len(addresses) == 1:
            destination = quote_plus(addresses[0])
            return f"{base_url}&destination={destination}"

        destination = quote_plus(addresses[-1])
        waypoints = "%7C".join(quote_plus(addr) for addr in addresses[:-1])
        return f"{base_url}&destination={destination}&waypoints={waypoints}"

    def _build_rotas_message(
        self,
        entregador_nome: str | None,
        pedidos: list[PedidoUnificadoModel],
    ) -> tuple[str, str]:
        quantidade = len(pedidos)
        primeiro_nome = (entregador_nome or "").strip().split(" ")[0] or "!"
        saudacao = f"Olá {primeiro_nome}! Seguem {quantidade} pedido(s) em rota de entrega:"

        linhas: list[str] = []
        for pedido_item in pedidos:
            partes = [pedido_item.numero_pedido or f"#{pedido_item.id}"]
            cliente = getattr(pedido_item, "cliente", None)
            cliente_nome = getattr(cliente, "nome", None)
            if cliente_nome:
                partes.append(cliente_nome)
            endereco = self._format_endereco_snapshot(self._extract_endereco_snapshot(pedido_item))
            if endereco:
                partes.append(endereco)
            linha = " - ".join(partes)
            valor_total = getattr(pedido_item, "valor_total", None)
            if valor_total is not None:
                try:
                    linha += f" - Valor: R$ {float(valor_total):.2f}"
                except (TypeError, ValueError):
                    pass
            linhas.append(linha)

        rota = self._build_google_maps_link(pedidos)
        mensagem_partes = [saudacao, "\n".join(linhas)]
        if rota:
            mensagem_partes.append(f"Rota no Google Maps: {rota}")

        mensagem = "\n\n".join(part for part in mensagem_partes if part)
        titulo = f"Rotas de entrega ({quantidade})"
        return titulo, mensagem

    def _notificar_entregador_rotas(self, pedido: PedidoUnificadoModel) -> None:
        if not pedido or not getattr(pedido, "entregador_id", None):
            return

        try:
            entregador = getattr(pedido, "entregador", None)
            if not entregador or not getattr(entregador, "telefone", None):
                entregador = self.repo_entregador.get(pedido.entregador_id)

            if not entregador:
                logger.warning(
                    "[Pedidos] Entregador %s não encontrado para notificação de rota",
                    pedido.entregador_id,
                )
                return

            telefone_raw = getattr(entregador, "telefone", None)
            telefone = str(telefone_raw).strip() if telefone_raw is not None else ""
            if not telefone:
                logger.warning(
                    "[Pedidos] Entregador %s sem telefone válido para WhatsApp",
                    entregador.id,
                )
                return

            pedidos_em_rota = self.repo.list_pedidos_em_rota_por_entregador(entregador.id)
            if not pedidos_em_rota:
                logger.info(
                    "[Pedidos] Nenhum pedido em rota para o entregador %s no momento",
                    entregador.id,
                )
                return

            if not self._whatsapp_config_valida(getattr(pedido, "empresa_id", None)):
                logger.warning("[Pedidos] Configurações do WhatsApp (chatbot) ausentes; notificação não enviada")
                return

            title, message = self._build_rotas_message(getattr(entregador, "nome", ""), pedidos_em_rota)
            whatsapp_message = f"*{title}*\n\n{message}"
            result = self._execute_async(
                lambda: OrderNotification.send_whatsapp_message(
                    telefone,
                    whatsapp_message,
                    getattr(pedido, "empresa_id", None),
                )
            )

            if not result:
                logger.error(
                    "[Pedidos] Falha ao enviar WhatsApp para o entregador %s (sem retorno)",
                    entregador.id,
                )
                return

            if isinstance(result, dict) and result.get("success"):
                logger.info(
                    "[Pedidos] Mensagem WhatsApp enviada para o entregador %s",
                    entregador.id,
                )
            else:
                logger.error(
                    "[Pedidos] Erro ao enviar WhatsApp para o entregador %s: %s",
                    entregador.id,
                    (result.get("error") if isinstance(result, dict) else str(result) if result else "erro desconhecido"),
                )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[Pedidos] Falha ao notificar entregador %s: %s",
                getattr(pedido, "entregador_id", None),
                exc,
            )

    def testar_busca_regiao(self, distancia_km: float, empresa_id: int) -> dict:
        """Método auxiliar para testar a busca de faixa por distância."""
        distancia = Decimal(str(distancia_km))

        regiao = self.taxa_service.regiao_repo.get_by_distancia(empresa_id, distancia)
        total = len(self.taxa_service.regiao_repo.list_by_empresa(empresa_id))

        return {
            "empresa_id": empresa_id,
            "distancia_km": float(distancia),
            "faixa_encontrada": regiao.id if regiao else None,
            "total_faixas": total,
        }

    def alterar_modo_edicao(self, pedido_id: int, modo_edicao: bool) -> PedidoResponse:
        """Altera o modo de edição do pedido."""
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        if modo_edicao:
            novo_status = PedidoStatusEnum.X.value
            motivo = "Modo de edição ativado"
        else:
            novo_status = PedidoStatusEnum.D.value
            motivo = "Modo de edição finalizado"

        self.repo.atualizar_status_pedido(pedido, novo_status, motivo)
        self.repo.commit()

        pedido = self.repo.get_pedido(pedido_id)
        return self._pedido_to_response(pedido)

    async def consultar_pagamento_gateway(
        self,
        *,
        gateway: PagamentoGatewayEnum,
        provider_transaction_id: str,
    ):
        return await self.pagamentos.consultar_gateway(
            gateway=gateway,
            provider_transaction_id=provider_transaction_id,
        )

    def calcular_preview_checkout(
        self,
        payload: FinalizarPedidoRequest,
        cliente_id: Optional[int] = None,
    ) -> PreviewCheckoutResponse:
        """Calcula o preview do checkout sem criar o pedido no banco de dados."""
        # Suporta tanto o formato novo (payload.produtos.*) quanto o legado (itens/receitas/combos na raiz)
        produtos_payload = getattr(payload, "produtos", None)
        if produtos_payload is not None:
            itens_normais = produtos_payload.itens or []
            receitas_req = getattr(produtos_payload, "receitas", None) or []
            combos_req = getattr(produtos_payload, "combos", None) or []
        else:
            itens_normais = payload.itens or []
            receitas_req = getattr(payload, "receitas", None) or []
            combos_req = getattr(payload, "combos", None) or []

        if not itens_normais and not receitas_req and not combos_req:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if (len(itens_normais) + len(receitas_req)) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        endereco = None
        if payload.tipo_entrega == TipoEntregaEnum.DELIVERY:
            if not payload.endereco_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço é obrigatório para delivery")
            
            endereco = self.repo.get_endereco(payload.endereco_id)
            if not endereco:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Endereço não encontrado")
            
            if cliente_id and endereco.cliente_id != cliente_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço não pertence ao cliente")

        empresa_id = payload.empresa_id
        empresa = None
        if payload.tipo_entrega == TipoEntregaEnum.DELIVERY:
            empresa, _ = self._resolver_empresa_delivery(
                endereco=endereco,
                empresa_id=empresa_id,
                itens=itens_normais,
            )
            empresa_id = empresa.id
            payload.empresa_id = empresa_id
        else:
            if not empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empresa é obrigatória para este tipo de pedido.")
            empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
            if not empresa:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        subtotal = Decimal("0")

        # Itens normais (produtos com código de barras)
        for item in itens_normais:
            if self.produto_contract is not None:
                pe_dto = self.produto_contract.obter_produto_emp_por_cod(empresa_id, item.produto_cod_barras)
                if not pe_dto:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {item.produto_cod_barras} não encontrado")
                if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {item.produto_cod_barras}")
                
                preco = _dec(pe_dto.preco_venda)
                subtotal += preco * item.quantidade
                # adicionais do item entram no subtotal
                subtotal += self._calcular_total_adicionais_item(empresa_id, item)
            else:
                produto_emp = self.repo.get_produto_emp(empresa_id, item.produto_cod_barras)
                if not produto_emp:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {item.produto_cod_barras} não encontrado")
                if not produto_emp.disponivel or not (produto_emp.produto and produto_emp.produto.ativo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {item.produto_cod_barras}")
                
                preco = _dec(produto_emp.preco_venda)
                subtotal += preco * item.quantidade
                subtotal += self._calcular_total_adicionais_item(empresa_id, item)

        # Receitas no preview
        for rec in receitas_req:
            qtd_rec = max(int(getattr(rec, "quantidade", 1) or 1), 1)
            
            # Busca receita do banco
            receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == rec.receita_id).first()
            
            # Usa ProductCore para buscar e validar
            product = self.product_core.buscar_receita(
                receita_id=rec.receita_id,
                empresa_id=empresa_id,
                receita_model=receita_model,
            )
            
            if not product:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Receita {rec.receita_id} não encontrada ou inativa",
                )
            
            if not self.product_core.validar_empresa(product, empresa_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Receita {rec.receita_id} não pertence à empresa {empresa_id}",
                )

            # Calcula preço com complementos usando ProductCore
            complementos_rec = getattr(rec, "complementos", None) or []
            preco_total_rec, _ = self.product_core.calcular_preco_com_complementos(
                product=product,
                quantidade=qtd_rec,
                complementos_request=complementos_rec,
            )
            subtotal += preco_total_rec

        # Combos opcionais no preview (base + adicionais de combo, se existirem)
        for cb in combos_req or []:
            qtd_combo = max(int(getattr(cb, "quantidade", 1) or 1), 1)
            
            # Usa ProductCore para buscar e validar
            product = self.product_core.buscar_combo(cb.combo_id)
            
            if not product:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Combo {cb.combo_id} não encontrado ou inativo")
            
            if not self.product_core.validar_empresa(product, empresa_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Combo {cb.combo_id} não pertence à empresa {empresa_id}",
                )

            # Calcula preço com complementos usando ProductCore
            complementos_combo = getattr(cb, "complementos", None) or []
            preco_total_combo, _ = self.product_core.calcular_preco_com_complementos(
                product=product,
                quantidade=qtd_combo,
                complementos_request=complementos_combo,
            )
            subtotal += preco_total_combo

        desconto = self._aplicar_cupom(
            cupom_id=payload.cupom_id,
            subtotal=subtotal,
            empresa_id=empresa_id,
        )

        taxa_entrega, taxa_servico, distancia_km, tempo_estimado_min = self._calcular_taxas(
            tipo_entrega=payload.tipo_entrega if isinstance(payload.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(payload.tipo_entrega),
            subtotal=subtotal,
            endereco=endereco,
            empresa_id=empresa_id,
        )

        valor_total = subtotal - desconto + taxa_entrega + taxa_servico

        # Tempo estimado de entrega em minutos, baseado na região de entrega (faixa).
        # Fallback: se não houver tempo configurado na faixa, usa tempo_entrega_maximo da empresa (se existir).
        tempo_entrega_minutos = None
        if tempo_estimado_min is not None:
            try:
                tempo_entrega_minutos = float(tempo_estimado_min)
            except (TypeError, ValueError):
                tempo_entrega_minutos = None
        elif empresa is not None and getattr(empresa, "tempo_entrega_maximo", None) is not None:
            try:
                tempo_entrega_minutos = float(empresa.tempo_entrega_maximo)
            except (TypeError, ValueError):
                tempo_entrega_minutos = None

        return PreviewCheckoutResponse(
            subtotal=float(subtotal),
            taxa_entrega=float(taxa_entrega),
            taxa_servico=float(taxa_servico),
            valor_total=float(valor_total),
            desconto=float(desconto),
            distancia_km=float(distancia_km) if distancia_km is not None else None,
            empresa_id=empresa_id,
            tempo_entrega_minutos=tempo_entrega_minutos,
        )

    # --------------- Itens auxiliares ---------------
    def _montar_observacao_item(self, item_req):
        # Observação é um campo livre para o cliente/atendimento; não anexar dados de complementos aqui.
        return item_req.observacao or None

    def _resolver_adicionais_item_snapshot(self, item_req):
        from app.api.pedidos.utils.complementos import resolve_produto_complementos
        return resolve_produto_complementos(
            complemento_contract=self.complemento_contract,
            produto_cod_barras=getattr(item_req, "produto_cod_barras", None),
            complementos_request=getattr(item_req, "complementos", None),
            quantidade_item=getattr(item_req, "quantidade", 1),
        )

    def _calcular_total_adicionais_item(self, empresa_id: int, item_req) -> Decimal:
        total, _ = self._resolver_adicionais_item_snapshot(item_req)
        return total


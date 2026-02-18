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
from app.api.chatbot.core.config_whatsapp import load_whatsapp_config, format_phone_number
from app.api.chatbot.core.notifications import OrderNotification
from app.utils.logger import logger
from app.utils.database_utils import now_trimmed
from app.api.pedidos.utils.entregador_notification_debouncer import (
    schedule_entregador_rotas_notification,
)

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
        # Cache simples para resultados de preview: evita recalcular imediatamente em caso de erros repetidos.
        # Chave: hash do payload relevante (cliente_id, endereco_id, empresa_id, itens) -> valor: (timestamp, result_or_exception)
        # TTL curto para resultados positivos, TTL maior para erros de distância.
        self._preview_cache: dict = {}
        self._preview_cache_ttl_ok = 5        # segundos para resultados bem-sucedidos
        self._preview_cache_ttl_error = 30    # segundos para erros (ex.: fora da área)

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
        # Alguns fluxos de edição atualizam tabelas relacionais (ex.: complementos) via DELETE/INSERT.
        # Isso pode deixar relationships em memória desatualizados até expirar.
        # Para garantir que o subtotal reflita o estado atual, tentamos recalcular a partir de um pedido
        # recarregado do banco (best-effort, sem falhar o fluxo).
        try:
            pid = getattr(pedido, "id", None)
            if pid is not None:
                pedido_db = self.repo.get_pedido(int(pid))
                if pedido_db is not None:
                    pedido = pedido_db
        except Exception:
            pass

        # IMPORTANTE: Usa _calc_total do repositório que já soma complementos corretamente
        # via _calc_item_total que inclui _sum_complementos_total_relacional
        subtotal = self.repo._calc_total(pedido)
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
                    # NÃO soma ao subtotal aqui - será recalculado depois usando _calc_total
                    # que já inclui complementos corretamente
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
                    # NÃO soma ao subtotal aqui - será recalculado depois usando _calc_total
                    # que já inclui complementos corretamente
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

                # REMOVIDO: adicionais_total, _ = self._resolver_adicionais_item_snapshot(it)
                # REMOVIDO: subtotal += adicionais_total
                # Os complementos serão somados corretamente quando _calc_total for chamado

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

                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
                # Os complementos são somados separadamente via _sum_complementos_total_relacional
                # para evitar duplicação no cálculo do total do item
                complementos_rec = getattr(rec, "complementos", None) or []
                preco_unit_rec = product.get_preco_venda()
                # O subtotal será recalculado depois incluindo complementos via _recalcular_pedido
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

                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
                # Os complementos são somados separadamente via _sum_complementos_total_relacional
                # para evitar duplicação no cálculo do total do item
                complementos_combo = getattr(cb, "complementos", None) or []
                secoes_selecionadas = getattr(cb, "secoes", None) or []
                # Combina complementos tradicionais com seleções de seções em um dict
                complementos_request = {"complementos": complementos_combo, "secoes": secoes_selecionadas}
                # Calcula preço total do combo incluindo incrementais de seções
                preco_total_combo, _ = self.product_core.calcular_preco_com_complementos(
                    product=product,
                    quantidade=qtd_combo,
                    complementos_request=complementos_request,
                )
                preco_unit_combo = preco_total_combo / Decimal(str(qtd_combo))
                # O subtotal será recalculado depois incluindo complementos via _recalcular_pedido
                observacao_combo = product.nome
                if hasattr(cb, 'observacao') and cb.observacao:
                    observacao_combo += f" | {cb.observacao}"
                
                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    combo_id=cb.combo_id,
                    quantidade=qtd_combo,
                    preco_unitario=preco_unit_combo,
                    observacao=observacao_combo,
                    produto_descricao_snapshot=product.nome or product.descricao,
                    complementos=complementos_request,
                )
            
            # IMPORTANTE: Recalcula o subtotal usando _calc_total que já inclui complementos
            # O subtotal calculado manualmente acima não inclui complementos de receitas/combos
            # e pode estar desatualizado. Usar _calc_total garante que todos os complementos sejam incluídos.
            pedido_atualizado = self.repo.get_pedido(pedido.id)
            subtotal = self.repo._calc_total(pedido_atualizado)
            
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

            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
                distancia_km=distancia_km,
            )

            # Define a previsão de entrega baseada no tempo estimado
            if tempo_estimado_min is not None and payload.tipo_entrega == TipoEntregaEnum.DELIVERY:
                try:
                    from datetime import timedelta
                    previsao_entrega = now_trimmed() + timedelta(minutes=int(tempo_estimado_min))
                    pedido.previsao_entrega = previsao_entrega
                    logger.info(f"[finalizar_pedido] Previsão de entrega definida: {previsao_entrega} (tempo estimado: {tempo_estimado_min} minutos)")
                except Exception as e:
                    logger.warning(f"[finalizar_pedido] Erro ao definir previsão de entrega: {e}")
            elif payload.tipo_entrega == TipoEntregaEnum.DELIVERY and empresa and getattr(empresa, "tempo_entrega_maximo", None) is not None:
                # Fallback: usa tempo_entrega_maximo da empresa se não houver tempo estimado da região
                try:
                    from datetime import timedelta
                    tempo_fallback = int(empresa.tempo_entrega_maximo)
                    previsao_entrega = now_trimmed() + timedelta(minutes=tempo_fallback)
                    pedido.previsao_entrega = previsao_entrega
                    logger.info(f"[finalizar_pedido] Previsão de entrega definida (fallback): {previsao_entrega} (tempo: {tempo_fallback} minutos)")
                except Exception as e:
                    logger.warning(f"[finalizar_pedido] Erro ao definir previsão de entrega (fallback): {e}")

            pedido.observacao_geral = payload.observacao_geral

            valor_total = _dec(pedido.valor_total or 0)
            
            if meios_pagamento_list:
                soma_pagamentos = sum(_dec(mp['valor']) for mp in meios_pagamento_list)
                if soma_pagamentos != valor_total:
                    # Ajuste best-effort para tolerar payloads do frontend/chatbot.
                    # Regra: ajusta SOMENTE o primeiro meio para fechar a conta, sem sobrescrever os demais.
                    # Isso evita inflar o total quando há múltiplos meios.
                    diferenca = valor_total - soma_pagamentos  # pode ser positiva (faltando) ou negativa (sobrando)
                    logger.warning(
                        f"[finalizar_pedido] Ajustando valores dos pagamentos para bater com o total do pedido: "
                        f"soma_pagamentos={float(soma_pagamentos)}, valor_total={float(valor_total)}, "
                        f"diferenca={float(diferenca)}"
                    )
                    if len(meios_pagamento_list) > 0:
                        valor0 = _dec(meios_pagamento_list[0]['valor'])
                        novo_valor0 = valor0 + diferenca
                        if novo_valor0 < 0:
                            raise HTTPException(
                                status.HTTP_400_BAD_REQUEST,
                                detail={
                                    "code": "PAGAMENTOS_INVALIDOS",
                                    "message": "Soma dos pagamentos excede o valor total do pedido.",
                                    "valor_total": float(valor_total),
                                    "soma_pagamentos": float(soma_pagamentos),
                                },
                            )
                        meios_pagamento_list[0]['valor'] = float(novo_valor0)
                        logger.info(
                            f"[finalizar_pedido] Primeiro meio ajustado para {float(novo_valor0)} (diferença aplicada: {float(diferenca)})"
                        )
            
            # Observação: troco_para não deve ser enviado pelo frontend/cliente.
            # O backend calcula troco automaticamente quando aplicável (ex.: pagamento em DINHEIRO com valor recebido > total).

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
                        # Ter meio de pagamento no checkout NÃO significa pago.
                        # Pagamento só deve ser confirmado via gateway (quando aplicável) ou via
                        # fechar-conta / marcar-pago.
                        status="PENDENTE",
                        provider_transaction_id=None,
                    )
                    
                    if is_pix_online_meio_pagamento(mp_obj):
                        try:
                            # Reutiliza a transação criada (evita duplicar registro no banco)
                            await self.pagamentos.iniciar_transacao(
                                pedido_id=pedido.id,
                                meio_pagamento_id=mp_obj.id,
                                valor=valor_parcial,
                                metodo=metodo,
                                gateway=gateway,
                                metadata={"pedido_id": pedido.id, "empresa_id": pedido.empresa_id},
                                transacao_id=transacao.id,
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
            from app.api.pedidos.utils.pedido_notification_helper import agendar_notificar_novo_pedido

            # Envia a notificação imediatamente após o checkout OK (sem bloquear a response).
            # Recarrega o pedido em nova sessão para evitar DetachedInstanceError.
            asyncio.create_task(agendar_notificar_novo_pedido(pedido_id=pedido.id, delay_seconds=0))
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

        # Múltiplos meios de pagamento: a fonte da verdade é `pedido.transacoes[]`.
        # Evita depender do relationship legado `pedido.transacao` (singular), que pode ter >1 linha no banco.
        transacoes = getattr(pedido, "transacoes", None) or []
        if any(getattr(tx, "status", None) in ("PAGO", "AUTORIZADO") for tx in transacoes):
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

    async def atualizar_status_pagamento_por_transacao_id(
        self,
        *,
        transacao_id: int,
        payload: TransacaoStatusUpdateRequest,
    ) -> PedidoResponse:
        transacao = await self.pagamentos.atualizar_status_por_transacao_id(
            transacao_id=transacao_id,
            payload=payload,
        )

        pedido_id = getattr(transacao, "pedido_id", None) or None
        if pedido_id is None:
            # Segurança: tenta recuperar pelo banco se necessário
            pedido = None
        else:
            pedido = self.repo.get_pedido(int(pedido_id))

        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        mudou_status = self._atualizar_status_pedido_por_pagamento(pedido, transacao.status)
        if mudou_status:
            self.repo.commit()
            pedido = self.repo.get_pedido(pedido.id)

        return self._pedido_to_response(pedido)

    async def atualizar_status_pagamento_por_provider_transaction_id(
        self,
        *,
        provider_transaction_id: str,
        payload: TransacaoStatusUpdateRequest,
    ) -> PedidoResponse:
        transacao = await self.pagamentos.atualizar_status_por_provider_transaction_id(
            provider_transaction_id=str(provider_transaction_id),
            payload=payload,
        )
        pedido_id = getattr(transacao, "pedido_id", None)
        if pedido_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido = self.repo.get_pedido(int(pedido_id))
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        mudou_status = self._atualizar_status_pedido_por_pagamento(pedido, transacao.status)
        if mudou_status:
            self.repo.commit()
            pedido = self.repo.get_pedido(pedido.id)

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

        # Para DELIVERY/RETIRADA, só permitimos marcar como ENTREGUE se o pedido já estiver pago.
        # Caso contrário, o fluxo correto é usar o endpoint fechar-conta (que registra a transação).
        if novo_status == PedidoStatusEnum.E and (pedido.is_delivery() or pedido.is_retirada()):
            from app.api.pedidos.services.service_pedido_helpers import build_pagamento_resumo

            pagamento_resumo = build_pagamento_resumo(pedido)
            ja_pago = bool(pagamento_resumo and getattr(pagamento_resumo, "esta_pago", False))
            if not ja_pago:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Não é possível setar status 'Entregue' para pedidos de delivery/retirada sem pagamento confirmado. "
                        "Use o endpoint 'fechar-conta' (ou marque como pago) antes de entregar."
                    ),
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

        # Gestor App: ao mudar para status "I" (Impressão), avisa em tempo real
        # da mesma forma que o checkout avisa (evento PEDIDO_CRIADO filtrado por rota "/gestor-app").
        # Importante: este gatilho é propositalmente restrito APENAS ao status I.
        if novo_status == PedidoStatusEnum.I:
            try:
                from app.api.notifications.core.ws_events import WSEvents
                from app.api.notifications.core.websocket_manager import websocket_manager

                empresa_id_str = str(pedido.empresa_id) if pedido.empresa_id is not None else ""
                if empresa_id_str:
                    tipo_entrega_val = (
                        pedido.tipo_entrega.value
                        if hasattr(pedido.tipo_entrega, "value")
                        else str(pedido.tipo_entrega)
                    )
                    numero_pedido_val = getattr(pedido, "numero_pedido", None)

                    payload = {
                        "pedido_id": str(pedido.id),
                        "tipo_entrega": tipo_entrega_val,
                        "status": novo_status.value,
                    }
                    if numero_pedido_val:
                        payload["numero_pedido"] = str(numero_pedido_val)

                    def _emit_gestor_app_event() -> None:
                        try:
                            asyncio.run(
                                websocket_manager.emit_event(
                                    event=WSEvents.PEDIDO_CRIADO,
                                    scope="empresa",
                                    empresa_id=empresa_id_str,
                                    payload=payload,
                                    required_route="/gestor-app",
                                )
                            )
                        except Exception as e:
                            logger.error(
                                "[WS] Erro ao avisar gestor-app (status I) pedido %s: %s",
                                pedido.id,
                                e,
                                exc_info=True,
                            )

                    threading.Thread(target=_emit_gestor_app_event, daemon=True).start()
            except Exception as e:
                logger.error(
                    "[WS] Erro ao agendar aviso gestor-app (status I) pedido %s: %s",
                    pedido.id,
                    e,
                    exc_info=True,
                )
        if novo_status == PedidoStatusEnum.S and pedido.entregador_id:
            schedule_entregador_rotas_notification(
                empresa_id=int(pedido.empresa_id),
                entregador_id=int(pedido.entregador_id),
                pedido_id=int(pedido.id),
            )
        
        # Envia notificação ao cliente quando pedido sai para entrega
        if novo_status == PedidoStatusEnum.S:
            try:
                # Extrai dados necessários antes de passar para a thread
                pedido_id = int(pedido.id)
                empresa_id_val = int(pedido.empresa_id) if pedido.empresa_id else None
                
                # Executa notificação em thread separada para não bloquear
                threading.Thread(
                    target=lambda: asyncio.run(self._notificar_cliente_pedido_em_rota(pedido_id, empresa_id_val)),
                    daemon=True
                ).start()
            except Exception as e:
                # Loga erro mas não quebra o fluxo
                logger.error(f"Erro ao agendar notificação de pedido em rota {pedido.id}: {e}")

        # Envia notificação ao cliente quando pedido é cancelado (status C)
        if novo_status == PedidoStatusEnum.C:
            try:
                _pid = int(pedido.id)
                _eid = int(pedido.empresa_id) if pedido.empresa_id else None
                from app.api.pedidos.utils.pedido_notification_helper import notificar_cliente_pedido_cancelado
                threading.Thread(
                    target=lambda p=_pid, e=_eid: asyncio.run(notificar_cliente_pedido_cancelado(p, e)),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error(f"Erro ao agendar notificação de cancelamento {pedido.id}: {e}")

            # Notifica frontend/kanban (evento WS) para atualizar listas em tempo real
            try:
                _pid = int(pedido.id)
                _eid = int(pedido.empresa_id) if pedido.empresa_id else None
                from app.api.pedidos.utils.pedido_notification_helper import notificar_pedido_cancelado
                _cancelado_por = str(user_id) if user_id is not None else "admin"
                threading.Thread(
                    target=lambda p=_pid, e=_eid, c=_cancelado_por: asyncio.run(
                        notificar_pedido_cancelado(
                            p,
                            e,
                            motivo="Pedido cancelado",
                            cancelado_por=c,
                        )
                    ),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error(f"Erro ao agendar notificação WS de cancelamento {pedido.id}: {e}")
        
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
        # Observação: editar pedido parcial não aceita mais troco enviado pelo frontend.
        # O cálculo de troco é responsabilidade do backend quando necessário.

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

            # Atualiza quantidade e observação
            quantidade_alterada = False
            if item.quantidade is not None and item.quantidade != it_db.quantidade:
                it_db.quantidade = item.quantidade
                quantidade_alterada = True
            if item.observacao is not None:
                it_db.observacao = item.observacao

            # Processa complementos se fornecidos
            if item.complementos is not None:
                # Remove complementos antigos do item
                from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
                complementos_antigos = self.db.query(PedidoItemComplementoModel).filter(
                    PedidoItemComplementoModel.pedido_item_id == it_db.id
                ).all()
                for comp_antigo in complementos_antigos:
                    self.db.delete(comp_antigo)
                self.db.flush()

                # Busca o produto/receita/combo para calcular preço com complementos
                product = None
                if it_db.produto_cod_barras:
                    product = self.product_core.buscar_produto(
                        empresa_id=pedido.empresa_id,
                        cod_barras=str(it_db.produto_cod_barras)
                    )
                elif it_db.receita_id:
                    receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == it_db.receita_id).first()
                    product = self.product_core.buscar_receita(receita_id=it_db.receita_id, receita_model=receita_model)
                elif it_db.combo_id:
                    product = self.product_core.buscar_combo(combo_id=it_db.combo_id)

                if product:
                    # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
                    # Os complementos são somados separadamente via _sum_complementos_total_relacional
                    # para evitar duplicação no cálculo do total do item
                    quantidade_item = item.quantidade if item.quantidade is not None else it_db.quantidade
                    preco_base_produto = product.get_preco_venda()
                    it_db.preco_unitario = preco_base_produto
                    # preco_total é apenas produto base * quantidade (sem complementos)
                    it_db.preco_total = preco_base_produto * Decimal(str(quantidade_item))
                else:
                    # Se não encontrou o produto, ainda persiste os complementos
                    # (o preço será recalculado depois)
                    pass

                # Persiste novos complementos
                self.repo._persistir_complementos_do_request(
                    item=it_db,
                    pedido_id=pedido_id,
                    complementos_request=item.complementos,
                )
            elif quantidade_alterada:
                # Se quantidade mudou mas não há complementos, recalcula apenas o preço total
                it_db.preco_total = it_db.preco_unitario * Decimal(str(it_db.quantidade))

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
            # Sempre notifica o entregador quando é vinculado, independente do status
            schedule_entregador_rotas_notification(
                empresa_id=int(pedido.empresa_id),
                entregador_id=int(pedido.entregador_id),
                pedido_id=int(pedido.id),
            )
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
            # Prioriza o endereço formatado ao invés de coordenadas
            formatted = self._format_endereco_snapshot(snapshot)
            if formatted:
                addresses.append(formatted)
            else:
                # Se não houver endereço formatado, usa coordenadas como fallback
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

    def _notificar_entregador_rotas(
        self,
        pedido: PedidoUnificadoModel,
        *,
        extra_pedidos: Optional[list[PedidoUnificadoModel]] = None,
    ) -> None:
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
            telefone_original = str(telefone_raw).strip() if telefone_raw is not None else ""
            if not telefone_original:
                logger.warning(
                    "[Pedidos] Entregador %s sem telefone válido para WhatsApp",
                    entregador.id,
                )
                return
            
            # Formata o telefone: remove caracteres não numéricos e garante código do país +55
            telefone = format_phone_number(telefone_original)
            
            logger.info(
                "[Pedidos] Telefone do entregador %s - Original: '%s' - Formatado: '%s' (DDD: %s)",
                entregador.id,
                telefone_original,
                telefone,
                telefone[2:4] if len(telefone) >= 4 else "N/A"
            )

            pedidos_em_rota = list(self.repo.list_pedidos_em_rota_por_entregador(entregador.id) or [])

            # Garante que o pedido "âncora" esteja incluído, mesmo que ainda não esteja com status "S".
            pedido_ids = {p.id for p in pedidos_em_rota}
            if pedido.id not in pedido_ids and pedido.tipo_entrega == TipoEntrega.DELIVERY.value:
                pedidos_em_rota.append(pedido)
                pedido_ids.add(pedido.id)

            # Inclui pedidos extras (ex.: múltiplas vinculações em sequência com debounce).
            for extra in extra_pedidos or []:
                if not extra:
                    continue
                if getattr(extra, "id", None) in pedido_ids:
                    continue
                if getattr(extra, "tipo_entrega", None) != TipoEntrega.DELIVERY.value:
                    continue
                # Mantém apenas pedidos do mesmo entregador (segurança).
                if getattr(extra, "entregador_id", None) != entregador.id:
                    continue
                pedidos_em_rota.append(extra)
                pedido_ids.add(extra.id)
            
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
            
            logger.info(
                "[Pedidos] Preparando envio WhatsApp para entregador %s - Telefone: %s - Pedidos: %s - Mensagem: %s",
                entregador.id,
                telefone,
                [p.id for p in pedidos_em_rota],
                whatsapp_message[:100] + "..." if len(whatsapp_message) > 100 else whatsapp_message
            )
            
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
                    "[Pedidos] Mensagem WhatsApp enviada para o entregador %s - Telefone: %s - Message ID: %s",
                    entregador.id,
                    telefone,
                    result.get("message_id", "N/A")
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

    async def _notificar_cliente_pedido_em_rota(self, pedido_id: int, empresa_id: Optional[int] = None) -> None:
        """
        Notifica o cliente quando o pedido sai para entrega.
        
        Args:
            pedido_id: ID do pedido que mudou para status "Saiu para entrega"
            empresa_id: ID da empresa (opcional)
        """
        # Cria uma nova sessão do banco para a thread assíncrona
        from app.database.db_connection import SessionLocal
        db_session = SessionLocal()
        
        try:
            # Recarrega o pedido com os relacionamentos necessários
            from sqlalchemy.orm import joinedload
            pedido = (
                db_session.query(PedidoUnificadoModel)
                .options(
                    joinedload(PedidoUnificadoModel.cliente),
                    joinedload(PedidoUnificadoModel.empresa),
                )
                .filter(PedidoUnificadoModel.id == pedido_id)
                .first()
            )
            
            if not pedido:
                logger.warning(
                    "[Pedidos] Pedido %s não encontrado para notificação de entrega",
                    pedido_id
                )
                return
            
            # Verifica se é um pedido de delivery
            if not pedido.is_delivery():
                return
            
            # Verifica se o pedido tem cliente
            if not pedido.cliente:
                logger.warning(
                    "[Pedidos] Pedido %s sem cliente para notificação de entrega",
                    pedido_id
                )
                return
            
            # Verifica se o cliente tem telefone
            telefone_raw = getattr(pedido.cliente, "telefone", None)
            if not telefone_raw:
                logger.warning(
                    "[Pedidos] Cliente %s do pedido %s sem telefone para notificação",
                    pedido.cliente.id,
                    pedido_id
                )
                return
            
            telefone_original = str(telefone_raw).strip()
            if not telefone_original:
                logger.warning(
                    "[Pedidos] Telefone do cliente %s do pedido %s está vazio",
                    pedido.cliente.id,
                    pedido_id
                )
                return
            
            # Formata o telefone
            telefone = format_phone_number(telefone_original)
            
            # Obtém o nome do cliente
            cliente_nome = getattr(pedido.cliente, "nome", "Cliente")
            
            # Formata a mensagem
            mensagem = f"""🛵 *Seu pedido está a caminho!*

Olá *{cliente_nome}*! 👋

Seu pedido *#{pedido.numero_pedido}* já saiu para entrega e está a caminho do endereço informado.

Em breve estará com você! 🚚

_Qualquer dúvida, entre em contato conosco._"""
            
            # Envia via WhatsApp
            # Resolve empresa_id de forma robusta (alguns pedidos podem ter empresa_id nulo,
            # mas ainda terem relacionamento empresa carregado)
            empresa_id_resolvido = (
                (int(pedido.empresa_id) if pedido.empresa_id else None)
                or (int(getattr(pedido.empresa, "id", 0)) if getattr(pedido, "empresa", None) else None)
                or (int(empresa_id) if empresa_id else None)
            )
            if not empresa_id_resolvido:
                logger.warning(
                    "[Pedidos] Pedido %s sem empresa_id resolvível; notificação 'em rota' omitida",
                    pedido_id,
                )
                return

            empresa_id_str = str(empresa_id_resolvido)
            whatsapp_result = await OrderNotification.send_whatsapp_message(
                telefone,
                mensagem,
                empresa_id=empresa_id_str
            )
            
            # Salva no chat interno também
            order_type = "delivery"
            # Obtém empresa_id do pedido (converte para int se necessário)
            empresa_id_int = empresa_id_resolvido
            whatsapp_message_id = whatsapp_result.get("message_id") if isinstance(whatsapp_result, dict) else None
            await OrderNotification.send_notification_async(
                db=db_session,
                phone=telefone,
                message=mensagem,
                order_type=order_type,
                empresa_id=empresa_id_int,
                whatsapp_message_id=whatsapp_message_id,
            )
            
            if whatsapp_result.get("success"):
                logger.info(
                    "[Pedidos] Notificação de entrega enviada ao cliente %s (pedido %s) via WhatsApp",
                    pedido.cliente.id,
                    pedido_id
                )
            else:
                logger.warning(
                    "[Pedidos] Erro ao enviar WhatsApp ao cliente %s (pedido %s): %s. Mensagem salva no chat interno.",
                    pedido.cliente.id,
                    pedido_id,
                    whatsapp_result.get("error", "erro desconhecido")
                )
            
        except Exception as exc:
            logger.error(
                "[Pedidos] Falha ao notificar cliente sobre pedido em rota %s: %s",
                pedido_id,
                exc,
                exc_info=True
            )
        finally:
            # Fecha a sessão do banco
            db_session.close()

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
        # --- CACHE: evita recalculos pesados/duplicados em sequência ---
        try:
            import json, hashlib, time

            def _payload_key():
                # Construir string resumida do payload relevante
                produtos_payload = getattr(payload, "produtos", None)
                if produtos_payload is not None:
                    itens = produtos_payload.itens or []
                    receitas = getattr(produtos_payload, "receitas", None) or []
                    combos = getattr(produtos_payload, "combos", None) or []
                else:
                    itens = payload.itens or []
                    receitas = getattr(payload, "receitas", None) or []
                    combos = getattr(payload, "combos", None) or []

                key_obj = {
                    "cliente_id": cliente_id,
                    "empresa_id": getattr(payload, "empresa_id", None),
                    "endereco_id": getattr(payload, "endereco_id", None),
                    "itens": [
                        {"cod": getattr(i, "produto_cod_barras", None), "q": getattr(i, "quantidade", None)}
                        for i in itens
                    ],
                    "receitas_len": len(receitas),
                    "combos_len": len(combos),
                }
                s = json.dumps(key_obj, sort_keys=True, ensure_ascii=True)
                return hashlib.sha1(s.encode("utf-8")).hexdigest()

            key = _payload_key()
            now_ts = time.time()
            cached = self._preview_cache.get(key)
            if cached:
                ts, stored = cached
                # stored can be tuple ("ok", response_dict) or ("err", exception_instance)
                # decide TTL based on stored type
                kind = stored[0]
                ttl = self._preview_cache_ttl_ok if kind == "ok" else self._preview_cache_ttl_error
                if now_ts - ts < ttl:
                    # Reaplicar: se era erro, re-raise; se era ok, retornar cópia
                    if kind == "err":
                        raise stored[1]
                    else:
                        # Reconstruir PreviewCheckoutResponse a partir do dict
                        data = stored[1]
                        return PreviewCheckoutResponse(**data)
        except Exception:
            # qualquer erro no cache não deve impedir o fluxo normal
            pass
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

        # IMPORTANTE (mesa/balcão no preview):
        # O schema `FinalizarPedidoRequest` ajusta `tipo_entrega` para RETIRADA quando `tipo_pedido`
        # é MESA/BALCAO. Para o cálculo correto de taxa de serviço (sempre 0 em mesa/balcão),
        # precisamos derivar o tipo real a partir de `tipo_pedido`.
        tipo_preview: TipoEntregaEnum
        if payload.tipo_pedido == TipoPedidoCheckoutEnum.MESA:
            tipo_preview = TipoEntregaEnum.MESA
        elif payload.tipo_pedido == TipoPedidoCheckoutEnum.BALCAO:
            tipo_preview = TipoEntregaEnum.BALCAO
        else:
            tipo_preview = (
                payload.tipo_entrega
                if isinstance(payload.tipo_entrega, TipoEntregaEnum)
                else TipoEntregaEnum(payload.tipo_entrega)
            )

        endereco = None
        if tipo_preview == TipoEntregaEnum.DELIVERY:
            if not payload.endereco_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço é obrigatório para delivery")
            
            endereco = self.repo.get_endereco(payload.endereco_id)
            if not endereco:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Endereço não encontrado")
            
            if cliente_id and endereco.cliente_id != cliente_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço não pertence ao cliente")

        empresa_id = payload.empresa_id
        empresa = None
        if tipo_preview == TipoEntregaEnum.DELIVERY:
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
            secoes_selecionadas = getattr(cb, "secoes", None) or []
            complementos_request = {"complementos": complementos_combo, "secoes": secoes_selecionadas}
            preco_total_combo, _ = self.product_core.calcular_preco_com_complementos(
                product=product,
                quantidade=qtd_combo,
                complementos_request=complementos_request,
            )
            subtotal += preco_total_combo

        desconto = self._aplicar_cupom(
            cupom_id=payload.cupom_id,
            subtotal=subtotal,
            empresa_id=empresa_id,
        )

        taxa_entrega, taxa_servico, distancia_km, tempo_estimado_min = self._calcular_taxas(
            tipo_entrega=tipo_preview,
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

        result = PreviewCheckoutResponse(
            subtotal=float(subtotal),
            taxa_entrega=float(taxa_entrega),
            taxa_servico=float(taxa_servico),
            valor_total=float(valor_total),
            desconto=float(desconto),
            distancia_km=float(distancia_km) if distancia_km is not None else None,
            empresa_id=empresa_id,
            tempo_entrega_minutos=tempo_entrega_minutos,
        )
        # Armazena no cache (resultado OK) — tenta model_dump para serializar
        try:
            import time
            now_ts = time.time()
            self._preview_cache[key] = (now_ts, ("ok", result.model_dump()))
        except Exception:
            # Log or handle the serialization error before returning result
            import logging
            logging.exception("Failed to serialize PreviewCheckoutResponse for cache.")
        return result

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


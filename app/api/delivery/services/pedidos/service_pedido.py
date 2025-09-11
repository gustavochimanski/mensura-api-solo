from __future__ import annotations

from datetime import date
from decimal import  ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
from app.api.delivery.models.model_pedido_item_dv import PedidoItemModel
from app.api.delivery.repositories.repo_pedidos import PedidoRepository
from app.api.delivery.services.meio_pagamento_service import MeioPagamentoService
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.schema_pedido import (
    FinalizarPedidoRequest, PedidoResponse, ItemPedidoResponse, PedidoKanbanResponse,
    EditarPedidoRequest, ItemPedidoEditar
)
from app.api.delivery.schemas.schema_shared_enums import (
    PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum,
    PagamentoMetodoEnum, PagamentoGatewayEnum, PagamentoStatusEnum
)
from app.api.delivery.services.service_pagamento_gateway import PaymentGatewayClient
from app.utils.logger import logger
from math import radians, cos, sin, asin, sqrt

from decimal import Decimal
from sqlalchemy import func

QTD_MAX_ITENS = 200

def _dec(value: float | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PedidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.gateway = PaymentGatewayClient()  # MOCK

    # Helper para recalcular e persistir os totais do pedido
    def _recalcular_pedido(self, pedido: PedidoDeliveryModel):
        """Recalcula subtotal, desconto, taxas e valor total do pedido e salva no banco."""
        # 1️⃣ Subtotal = soma de todos os itens
        subtotal = self.db.query(
            func.sum(PedidoItemModel.quantidade * PedidoItemModel.preco_unitario)
        ).filter(PedidoItemModel.pedido_id == pedido.id).scalar() or Decimal("0")

        subtotal = Decimal(subtotal)  # força Decimal

        # 2️⃣ Desconto do cupom
        desconto = self._aplicar_cupom(cupom_id=pedido.cupom_id, subtotal=subtotal)

        # 3️⃣ Taxas
        endereco = pedido.endereco  # relacionamento já carregado
        taxa_entrega, taxa_servico = self._calcular_taxas(
            tipo_entrega=pedido.tipo_entrega,
            subtotal=subtotal,
            endereco=endereco,
            empresa_id=pedido.empresa_id,
        )

        # 4️⃣ Atualiza no pedido
        pedido.subtotal = subtotal
        pedido.desconto = desconto
        pedido.taxa_entrega = taxa_entrega
        pedido.taxa_servico = taxa_servico
        pedido.valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        if pedido.valor_total < 0:
            pedido.valor_total = Decimal("0")

        # 5️⃣ Commit e refresh
        self.repo.commit()
        self.db.refresh(pedido)

    # ---------- Helper: monta a resposta padronizada ----------
    def _pedido_to_response(self, pedido) -> PedidoResponse:
        return PedidoResponse(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            telefone_cliente=pedido.cliente.telefone if pedido.cliente else None,  # ⚡ via relacionamento
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=(
                pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                else TipoEntregaEnum(pedido.tipo_entrega)
            ),
            origem=(
                pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                else OrigemPedidoEnum(pedido.origem)
            ),
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

        def haversine(lat1, lon1, lat2, lon2):
            """
            Retorna a distância em km entre dois pontos geográficos.
            """
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            km = 6371 * c  # raio da Terra em km
            return km

        # ------------------ cálculo da taxa ------------------
        taxa_entrega = _dec(0)
        if tipo_entrega == TipoEntregaEnum.DELIVERY and endereco and empresa_id:
            regioes = (
                self.db.query(RegiaoEntregaModel)
                .filter(RegiaoEntregaModel.empresa_id == empresa_id, RegiaoEntregaModel.ativo == True)
                .all()
            )

            regiao_encontrada = None
            for reg in regioes:
                distancia = haversine(endereco.latitude, endereco.longitude, reg.latitude, reg.longitude)
                if distancia <= float(2.0):  # reg.raio_km é o raio de entrega da região
                    regiao_encontrada = reg
                    break

            if not regiao_encontrada:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Não entregamos neste endereço (lat: {endereco.latitude}, lon: {endereco.longitude})"
                )

            taxa_entrega = _dec(regiao_encontrada.taxa_entrega)

        taxa_servico = (subtotal * Decimal("0.01")).quantize(Decimal("0.01"))
        return taxa_entrega, taxa_servico


    def _aplicar_cupom(self, *, cupom_id: Optional[int], subtotal: Decimal) -> Decimal:
        if not cupom_id:
            return _dec(0)
        cupom = self.repo.get_cupom(cupom_id)
        if not cupom or not cupom.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom inválido ou inativo")

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

    # ---------- Fluxo 1 ----------
    def finalizar_pedido(self, payload: FinalizarPedidoRequest, cliente_id: int) -> PedidoResponse:
        # Validações principais
        if not payload.itens:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if len(payload.itens) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        meio_pagamento = MeioPagamentoService(self.db).get(payload.meio_pagamento_id)
        if not meio_pagamento or not meio_pagamento.ativo:
            raise HTTPException(400, "Meio de pagamento inválido ou inativo")

        empresa = self.repo_empresa.get_empresa_by_id(payload.empresa_id)
        if not empresa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # Cliente
        cliente = self.repo.get_cliente_by_id(cliente_id)
        if not cliente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

        if payload.tipo_entrega == TipoEntregaEnum.DELIVERY and not payload.endereco_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço é obrigatório para delivery")

        endereco = None
        if payload.endereco_id:
            endereco = self.repo.get_endereco(payload.endereco_id)
            if not endereco or endereco.cliente_id != cliente_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço inválido para o cliente")

        try:
            status_inicial = (
                PedidoStatusEnum.R.value  # Em preparo
                if getattr(empresa, "aceita_pedido_automatico", False)
                else PedidoStatusEnum.P.value  # Pendente
            )
            pedido = self.repo.criar_pedido(
                cliente_id=cliente_id,
                empresa_id=payload.empresa_id,
                endereco_id=payload.endereco_id,
                meio_pagamento_id=payload.meio_pagamento_id,
                status=status_inicial,
                tipo_entrega=payload.tipo_entrega,
                origem=payload.origem.value,
            )

            subtotal = Decimal("0")
            for it in payload.itens:
                pe = self.repo.get_produto_emp(payload.empresa_id, it.produto_cod_barras)
                if not pe:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
                if not pe.disponivel or not (pe.produto and pe.produto.ativo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")

                preco = _dec(pe.preco_venda)
                subtotal += preco * it.quantidade
                logger.info(
                    f"Adicionando item ao pedido_id={pedido.id}: cod_barras={it.produto_cod_barras}, quantidade={it.quantidade}")
                self.repo.adicionar_item(
                    pedido=pedido,
                    pedido_id=pedido.id,
                    cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=preco,
                    observacao=it.observacao,
                    produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                    produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
                )


            desconto = self._aplicar_cupom(cupom_id=payload.cupom_id, subtotal=subtotal)
            taxa_entrega, taxa_servico = self._calcular_taxas(
                tipo_entrega=payload.tipo_entrega,
                subtotal=subtotal,
                endereco=endereco,
                empresa_id=payload.empresa_id,
            )

            logger.info(f'CLIENTE_ID: {cliente_id}')


            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
            )
            logger.info(f'CLIENTE_ID: {cliente_id}')

            pedido.observacao_geral = payload.observacao_geral
            if payload.troco_para:
                pedido.troco_para = _dec(payload.troco_para)
            logger.info(f'CLIENTE_ID: {cliente_id}')

            self.repo.commit()
            pedido = self.repo.get_pedido(pedido.id)  # já vem com joinedload

        except HTTPException:
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao finalizar pedido: {e}")

        return self._pedido_to_response(pedido)

    # ---------- Fluxo 2 ----------
    async def confirmar_pagamento(
        self,
        *,
        pedido_id: int,
        metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
        gateway: PagamentoGatewayEnum = PagamentoGatewayEnum.PIX_INTERNO,
    ) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        if pedido.valor_total is None or pedido.valor_total <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Valor total inválido para pagamento")

        # idempotência simples
        if pedido.transacao and pedido.transacao.status in ("PAGO", "AUTORIZADO"):
            return self._pedido_to_response(pedido)

        try:
            tx = self.repo.criar_transacao_pagamento(
                pedido_id=pedido.id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=_dec(pedido.valor_total),
            )

            result = await self.gateway.charge(
                order_id=pedido.id,
                amount=_dec(pedido.valor_total),
                metodo=metodo,
                gateway=gateway,
                metadata={"empresa_id": pedido.empresa_id},
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
                self.repo.atualizar_status_pedido(pedido, PedidoStatusEnum.A.value, motivo="Pagamento confirmado")
            else:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="RECUSADO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                )

            self.repo.commit()
            # recarrega para garantir itens/transação atualizados
            pedido = self.repo.get_pedido(pedido.id)
            return self._pedido_to_response(pedido)

        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao confirmar pagamento: {e}")

    def listar_pedidos(self, cliente_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponse]:
        pedidos = self.repo.db.query(PedidoDeliveryModel) \
            .filter(PedidoDeliveryModel.cliente_id == cliente_id) \
            .order_by(PedidoDeliveryModel.data_criacao.desc()) \
            .offset(skip).limit(limit).all()
        return [self._pedido_to_response(p) for p in pedidos]

    def get_pedido_by_id(self, pedido_id: int) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:

            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response(pedido)





    # ======================================================================
    # ============================ ADMIN ===================================
    # ======================================================================
    def list_all_kanban(self, limit: int = 500, date_filter: date | None = None, empresa_id: int=1):
        pedidos = self.repo.list_all_kanban(limit=limit, date_filter=date_filter, empresa_id=empresa_id)
        resultados = []

        for p in pedidos:
            cliente = p.cliente
            endereco = cliente.enderecos[0] if cliente and cliente.enderecos else None

            endereco_str = None
            if endereco:
                endereco_str = ", ".join(
                    filter(None, [
                        endereco.logradouro,
                        endereco.numero,
                        endereco.bairro,
                        endereco.cidade,
                        endereco.cep,
                        endereco.complemento
                    ])
                )

            resultados.append(
                PedidoKanbanResponse(
                    id=p.id,
                    status=p.status,
                    valor_total=p.valor_total,
                    data_criacao=p.data_criacao,
                    telefone_cliente=cliente.telefone if cliente else None,
                    nome_cliente=cliente.nome if cliente else None,
                    endereco_cliente=endereco_str,
                    meio_pagamento_descricao=p.meio_pagamento.display() if p.meio_pagamento else None,
                    observacao_geral=p.observacao_geral,
                    meio_pagamento_id=p.meio_pagamento.id
                )
            )

        return resultados

    # ====================== ATUALIZA PEDIDO ===============================
    # ======================================================================
    def atualizar_status(self, pedido_id: int, novo_status: str):
        pedido = self.db.query(PedidoDeliveryModel).filter_by(id=pedido_id).first()
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado"
            )

        pedido.status = novo_status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # ====================== EDITAR PEDIDO =================================
    # ======================================================================
    def editar_pedido_parcial(self, pedido_id: int, payload: EditarPedidoRequest) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Atualiza meio de pagamento
        if payload.meio_pagamento_id is not None:
            meio_pagamento = MeioPagamentoService(self.db).get(payload.meio_pagamento_id)
            if not meio_pagamento or not meio_pagamento.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")
            pedido.meio_pagamento_id = payload.meio_pagamento_id

        # Atualiza endereço
        if payload.endereco_id is not None:
            endereco = self.repo.get_endereco(payload.endereco_id)
            if not endereco:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Endereço não encontrado")
            pedido.endereco_id = payload.endereco_id
        else:
            endereco = None

        # Atualiza cupom
        if payload.cupom_id is not None:
            pedido.cupom_id = payload.cupom_id

        # Observação e troco
        if payload.observacao_geral is not None:
            pedido.observacao_geral = payload.observacao_geral
        if payload.troco_para is not None:
            pedido.troco_para = _dec(payload.troco_para)

        # Recalcula subtotal/taxas apenas se endereço ou cupom mudou
        subtotal = pedido.subtotal or 0
        desconto = self._aplicar_cupom(cupom_id=pedido.cupom_id, subtotal=subtotal)
        taxa_entrega, taxa_servico = self._calcular_taxas(
            tipo_entrega=pedido.tipo_entrega,
            subtotal=subtotal,
            endereco=endereco,
            empresa_id=pedido.empresa_id,
        )
        self.repo.atualizar_totais(pedido, subtotal=subtotal, desconto=desconto, taxa_entrega=taxa_entrega, taxa_servico=taxa_servico)

        self.repo.commit()
        pedido = self.repo.get_pedido(pedido.id)  # garantir cliente/endereco/meio_pagamento carregados
        return self._pedido_to_response(pedido)

    # ================== EDITAR ITENS PEDIDO ===============================
    # ======================================================================
    # Metodo completo de atualização de itens
    def atualizar_itens_pedido(self, pedido_id: int, itens: list[ItemPedidoEditar]) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        total_alterado = False

        for item in itens:
            if item.acao == "atualizar":
                if not item.id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "ID do item obrigatório para atualizar")
                it_db = self.repo.get_item_by_id(item.id)
                if not it_db:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item.id} não encontrado")

                if item.quantidade is not None and item.quantidade != it_db.quantidade:
                    it_db.quantidade = item.quantidade
                    total_alterado = True
                if item.observacao is not None:
                    it_db.observacao = item.observacao

            elif item.acao == "remover":
                if not item.id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "ID do item obrigatório para remover")
                it_db = self.repo.get_item_by_id(item.id)
                if not it_db:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item.id} não encontrado")
                self.db.delete(it_db)
                total_alterado = True

            elif item.acao == "novo-item":
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
                total_alterado = True

            else:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ação inválida: {item.acao}")

        if total_alterado:
            self.db.flush()  # garante itens atualizados
            self._recalcular_pedido(pedido)  # agora só faz flush interno
            self.repo.commit()  # 👍 commit centralizado
            pedido = self.repo.get_pedido(pedido.id)  # 👍 reconsulta com joinedload para resposta fresca
        return self._pedido_to_response(pedido)




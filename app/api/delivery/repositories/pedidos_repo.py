from __future__ import annotations
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import func, and_, select
from sqlalchemy.orm import Session, joinedload

from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel
from app.api.delivery.models.pedido_item_dv_model import PedidoItemModel
from app.api.delivery.models.pedido_status_historico_dv_model import PedidoStatusHistoricoModel
from app.api.delivery.models.cupom_dv_model import CupomDescontoModel
from app.api.delivery.models.endereco_dv_model import EnderecoDeliveryModel
from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.models.transacao_pagamento_dv_model import TransacaoPagamentoModel, PagamentoStatus

class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    # --------- Validations / Queries ----------
    def get_cliente(self, cliente_id: int) -> Optional[ClienteDeliveryModel]:
        return self.db.get(ClienteDeliveryModel, cliente_id)

    def get_endereco(self, endereco_id: int) -> Optional[EnderecoDeliveryModel]:
        return self.db.get(EnderecoDeliveryModel, endereco_id)

    def get_produto_emp(
        self, empresa_id: int, cod_barras: str
    ) -> Optional[ProdutoEmpDeliveryModel]:
        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoEmpDeliveryModel.cod_barras == cod_barras,
            )
            .first()
        )

    def get_cupom(self, cupom_id: int) -> Optional[CupomDescontoModel]:
        return self.db.get(CupomDescontoModel, cupom_id)

    def get_pedido(self, pedido_id: int) -> Optional[PedidoDeliveryModel]:
        return (
            self.db.query(PedidoDeliveryModel)
            .options(
                joinedload(PedidoDeliveryModel.itens),
                joinedload(PedidoDeliveryModel.transacao),
            )
            .filter(PedidoDeliveryModel.id == pedido_id)
            .first()
        )

    # --------- Mutations (atomic with outer service) ----------
    def criar_pedido(
        self,
        *,
        cliente_id: int | None,
        empresa_id: int,
        endereco_id: int | None,
        status: str = "P",
        tipo_entrega: str,
        origem: str,
    ) -> PedidoDeliveryModel:
        pedido = PedidoDeliveryModel(
            cliente_id=cliente_id,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            status=status,
            tipo_entrega=tipo_entrega,
            origem=origem,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        self.db.add(pedido)
        self.db.flush()  # gera id
        self.add_status_historico(pedido.id, status, motivo="Pedido criado")
        return pedido

    def adicionar_item(
        self,
        *,
        pedido_id: int,
        cod_barras: str,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        produto_descricao_snapshot: str | None,
        produto_imagem_snapshot: str | None,
    ) -> PedidoItemModel:
        item = PedidoItemModel(
            pedido_id=pedido_id,
            produto_cod_barras=cod_barras,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=produto_descricao_snapshot,
            produto_imagem_snapshot=produto_imagem_snapshot,
        )
        self.db.add(item)
        return item

    def atualizar_totais(
        self,
        pedido: PedidoDeliveryModel,
        *,
        subtotal: Decimal,
        desconto: Decimal,
        taxa_entrega: Decimal,
        taxa_servico: Decimal,
    ) -> None:
        pedido.subtotal = subtotal
        pedido.desconto = desconto
        pedido.taxa_entrega = taxa_entrega
        pedido.taxa_servico = taxa_servico
        pedido.valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        if pedido.valor_total < 0:
            pedido.valor_total = Decimal("0")

    def add_status_historico(
        self, pedido_id: int, status: str, motivo: str | None = None, criado_por: str | None = "system"
    ):
        hist = PedidoStatusHistoricoModel(
            pedido_id=pedido_id,
            status=status,
            motivo=motivo,
            criado_por=criado_por,
        )
        self.db.add(hist)

    def atualizar_status_pedido(self, pedido: PedidoDeliveryModel, novo_status: str, motivo: str | None = None):
        pedido.status = novo_status
        self.add_status_historico(pedido.id, novo_status, motivo=motivo)

    # --------- Transação de pagamento ----------
    def criar_transacao_pagamento(
        self,
        *,
        pedido_id: int,
        gateway: str,
        metodo: str,
        valor: Decimal,
        moeda: str = "BRL",
    ) -> TransacaoPagamentoModel:
        tx = TransacaoPagamentoModel(
            pedido_id=pedido_id,
            gateway=gateway,
            metodo=metodo,
            valor=valor,
            moeda=moeda,
            status="PENDENTE",
        )
        self.db.add(tx)
        self.db.flush()  # gera id
        return tx

    def atualizar_transacao_status(
        self,
        tx: TransacaoPagamentoModel,
        *,
        status: str,
        provider_transaction_id: str | None = None,
        payload_retorno: dict | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
        timestamp_field: str | None = None,  # "autorizado_em" | "pago_em" | ...
    ):
        tx.status = status
        if provider_transaction_id is not None:
            tx.provider_transaction_id = provider_transaction_id
        if payload_retorno is not None:
            tx.payload_retorno = payload_retorno
        if qr_code is not None:
            tx.qr_code = qr_code
        if qr_code_base64 is not None:
            tx.qr_code_base64 = qr_code_base64
        if timestamp_field:
            setattr(tx, timestamp_field, func.now())

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

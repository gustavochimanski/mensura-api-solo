from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from starlette import status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
from app.api.delivery.models.model_pedido_item_dv import PedidoItemModel
from app.api.delivery.models.model_pedido_status_historico_dv import PedidoStatusHistoricoModel
from app.api.delivery.models.model_cupom_dv import CupomDescontoModel
from app.api.delivery.models.model_endereco_dv import EnderecoDeliveryModel
from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.models.model_transacao_pagamento_dv import TransacaoPagamentoModel


class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------- Validations / Queries -------------
    def get_cliente(self, telefone: str) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter_by(telefone=telefone).first()

    def get_cliente_by_id(self, id: int) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter(ClienteDeliveryModel.id == id).first()

    def get_endereco(self, endereco_id: int) -> Optional[EnderecoDeliveryModel]:
        return self.db.get(EnderecoDeliveryModel, endereco_id)

    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .options(joinedload(ProdutoEmpModel.produto))
            .filter(
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.cod_barras == cod_barras,
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
                joinedload(PedidoDeliveryModel.cliente).joinedload(ClienteDeliveryModel.enderecos),
                joinedload(PedidoDeliveryModel.endereco),
                joinedload(PedidoDeliveryModel.meio_pagamento),
                joinedload(PedidoDeliveryModel.transacao),
            )
            .filter(PedidoDeliveryModel.id == pedido_id)
            .first()
        )

    def get_by_cliente_id(self, cliente_id: int) -> list[PedidoDeliveryModel]:
        """Busca todos os pedidos de um cliente específico"""
        return (
            self.db.query(PedidoDeliveryModel)
            .filter(PedidoDeliveryModel.cliente_id == cliente_id)
            .all()
        )

    def list_all_kanban(self, limit: int = 500, date_filter: date | None = None, empresa_id: int = 1):
        query = (
            self.db.query(PedidoDeliveryModel)
            .options(
                joinedload(PedidoDeliveryModel.cliente).joinedload(ClienteDeliveryModel.enderecos),
                joinedload(PedidoDeliveryModel.endereco),
                joinedload(PedidoDeliveryModel.meio_pagamento),
            )
            .filter(PedidoDeliveryModel.empresa_id == empresa_id)
        )

        query = query.order_by(PedidoDeliveryModel.data_criacao.desc())

        if date_filter:
            query = query.filter(func.date(PedidoDeliveryModel.data_criacao) == date_filter)

        return query.limit(limit).all()

    # -------------------- Mutations -------------------
    def criar_pedido(
        self,
        *,
        cliente_id: int | None,
        empresa_id: int,
        endereco_id: int | None,
        meio_pagamento_id: int,
        status: str = "I",
        tipo_entrega: str,
        origem: str,
        endereco_snapshot: dict | None = None,
        endereco_geo = None,
    ) -> PedidoDeliveryModel:
        # ⚠️ Setar SOMENTE os campos escalares/FKs aqui; nada de refresh agora
        pedido = PedidoDeliveryModel(
            cliente_id=int(cliente_id) if cliente_id is not None else None,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            meio_pagamento_id=meio_pagamento_id,
            status=status,
            tipo_entrega=tipo_entrega,
            origem=origem,
            endereco_snapshot=endereco_snapshot,
            endereco_geo=endereco_geo,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        self.db.add(pedido)
        self.db.flush()  # garante ID do pedido

        self.add_status_historico(pedido.id, status, motivo="Pedido criado")
        # ❌ NÃO fazer refresh aqui; evita rehidratar com potencial NULL de triggers/DFs
        return pedido

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
        # Apenas flush — não precisa de refresh
        self.db.flush()

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

    # ----------------- Transação pagamento -------------
    def criar_transacao_pagamento(
        self,
        *,
        pedido_id: int,
        meio_pagamento_id: int,
        gateway: str,
        metodo: str,
        valor: Decimal,
        moeda: str = "BRL",
        payload_solicitacao: dict | None = None,
        provider_transaction_id: str | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
    ) -> TransacaoPagamentoModel:
        tx = TransacaoPagamentoModel(
            pedido_id=pedido_id,
            meio_pagamento_id=meio_pagamento_id,
            gateway=gateway,
            metodo=metodo,
            valor=valor,
            moeda=moeda,
            status="PENDENTE",
            payload_solicitacao=payload_solicitacao,
            provider_transaction_id=provider_transaction_id,
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
        )
        self.db.add(tx)
        self.db.flush()
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
        timestamp_field: str | None = None,
        payload_solicitacao: dict | None = None,
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
        if payload_solicitacao is not None:
            tx.payload_solicitacao = payload_solicitacao
        if timestamp_field:
            setattr(tx, timestamp_field, func.now())

    # ---------------- Unit of Work ---------------------
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    # --------------- ITENS PEDIDO ----------------------
    def get_item_by_id(self, item_id: int) -> Optional[PedidoItemModel]:
        return self.db.get(PedidoItemModel, item_id)

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
        # ⚠️ Evitar passar o objeto pedido E o pedido_id juntos.
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
        self.db.flush()
        return item

    def atualizar_item(
        self,
        item_id: int,
        quantidade: int | None = None,
        observacao: str | None = None
    ) -> PedidoItemModel:
        item = self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item_id} não encontrado")
        if quantidade is not None:
            item.quantidade = quantidade
        if observacao is not None:
            item.observacao = observacao
        self.db.flush()
        return item

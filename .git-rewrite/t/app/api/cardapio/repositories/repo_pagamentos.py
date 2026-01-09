from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.api.cardapio.models.model_transacao_pagamento_dv import (
    TransacaoPagamentoModel,
)


class PagamentoRepository:
    """Repositório especializado para transações de pagamento."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------- Consultas -----------------
    def get_by_id(self, transacao_id: int) -> Optional[TransacaoPagamentoModel]:
        return self.db.get(TransacaoPagamentoModel, transacao_id)

    def get_by_pedido_id(self, pedido_id: int) -> Optional[TransacaoPagamentoModel]:
        return (
            self.db.query(TransacaoPagamentoModel)
            .filter(TransacaoPagamentoModel.pedido_id == pedido_id)
            .one_or_none()
        )

    # ---------------- Mutations ------------------
    def criar(
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
        status: str = "PENDENTE",
    ) -> TransacaoPagamentoModel:
        tx = TransacaoPagamentoModel(
            pedido_id=pedido_id,
            meio_pagamento_id=meio_pagamento_id,
            gateway=gateway,
            metodo=metodo,
            valor=valor,
            moeda=moeda,
            status=status,
            payload_solicitacao=payload_solicitacao,
            provider_transaction_id=provider_transaction_id,
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    def atualizar(
        self,
        tx: TransacaoPagamentoModel,
        *,
        status: Optional[str] = None,
        provider_transaction_id: str | None = None,
        payload_solicitacao: dict | None = None,
        payload_retorno: dict | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
    ) -> TransacaoPagamentoModel:
        if status is not None:
            tx.status = status
        if provider_transaction_id is not None:
            tx.provider_transaction_id = provider_transaction_id
        if payload_solicitacao is not None:
            tx.payload_solicitacao = payload_solicitacao
        if payload_retorno is not None:
            tx.payload_retorno = payload_retorno
        if qr_code is not None:
            tx.qr_code = qr_code
        if qr_code_base64 is not None:
            tx.qr_code_base64 = qr_code_base64
        self.db.flush()
        return tx

    def registrar_evento(self, tx: TransacaoPagamentoModel, campo_timestamp: str) -> None:
        from sqlalchemy import func

        setattr(tx, campo_timestamp, func.now())
        self.db.flush()

    # ---------------- Unidade de trabalho --------
    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()


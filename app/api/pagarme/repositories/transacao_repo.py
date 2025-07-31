# app/api/pagarme/repositories/transacao_repo.py

from sqlalchemy.orm import Session
from app.api.pagarme.models.transacao_model import TransacaoPagamentoModel


class TransacaoPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, dados: dict) -> TransacaoPagamentoModel:
        transacao = TransacaoPagamentoModel(**dados)
        self.db.add(transacao)
        self.db.commit()
        self.db.refresh(transacao)
        return transacao

    def atualizar_status(self, transacao_id: str, novo_status: str):
        transacao = self.db.query(TransacaoPagamentoModel).filter_by(id=transacao_id).first()
        if transacao:
            transacao.status = novo_status
            self.db.commit()
            self.db.refresh(transacao)
        return transacao

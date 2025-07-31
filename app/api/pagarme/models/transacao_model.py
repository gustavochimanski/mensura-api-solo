# app/api/pagarme/models/transacao_model.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.database.db_connection import Base
import enum


class MetodoPagamentoEnum(str, enum.Enum):
    boleto = "boleto"
    credit_card = "credit_card"
    pix = "pix"


class TransacaoPagamentoModel(Base):
    __tablename__ = "transacoes_pagamento"
    __table_args__ = {"schema": "payment"}

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    pedido_id = Column(ForeignKey("delivery.pedidos_dv.id", ondelete="CASCADE"), nullable=False)
    metodo = Column(SqlEnum(MetodoPagamentoEnum), nullable=False)
    status = Column(String(1), nullable=False)  # Ex: processing, paid, refused
    boleto_url = Column(String, nullable=True)
    pix_qr_code_url = Column(String, nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pedido = relationship("PedidoDeliveryModel", back_populates="transacao")

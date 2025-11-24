from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SAEnum, JSON, func, Index, UUID
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

PagamentoGateway = SAEnum("MERCADOPAGO", "PAGSEGURO", "STRIPE", "PIX_INTERNO", "OUTRO", name="pagamento_gateway_enum", create_type=False, schema="cardapio")
PagamentoMetodo  = SAEnum("PIX", "PIX_ONLINE", "CREDITO", "DEBITO", "DINHEIRO", "ONLINE", "OUTRO", name="pagamento_metodo_enum", create_type=False, schema="cardapio")
PagamentoStatus  = SAEnum("PENDENTE", "AUTORIZADO", "PAGO", "RECUSADO", "CANCELADO", "ESTORNADO", name="pagamento_status_enum", create_type=False, schema="cardapio")

class TransacaoPagamentoModel(Base):
    __tablename__ = "transacoes_pagamento_dv"
    __table_args__ = (
        Index("idx_transacao_pedido", "pedido_id"),
        {"schema": "cardapio"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.pedidos.id", ondelete="CASCADE"), nullable=False)

    gateway = Column(PagamentoGateway, nullable=False)
    metodo = Column(PagamentoMetodo, nullable=False)

    meio_pagamento_id = Column(Integer, ForeignKey("cadastros.meios_pagamento.id"), nullable=False)
    meio_pagamento = relationship("MeioPagamentoModel")

    valor = Column(Numeric(18, 2), nullable=False)
    moeda = Column(String(3), nullable=False, default="BRL")

    status = Column(PagamentoStatus, nullable=False, default="PENDENTE")

    provider_transaction_id = Column(String(120), nullable=True)
    qr_code = Column(String, nullable=True)
    qr_code_base64 = Column(String, nullable=True)

    payload_solicitacao = Column(JSON, nullable=True)
    payload_retorno = Column(JSON, nullable=True)

    autorizado_em = Column(DateTime(timezone=True), nullable=True)
    pago_em = Column(DateTime(timezone=True), nullable=True)
    cancelado_em = Column(DateTime(timezone=True), nullable=True)
    estornado_em = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed,  nullable=False)

    pedido = relationship("PedidoUnificadoModel", back_populates="transacao", overlaps="pedido_multi")
    pedido_multi = relationship("PedidoUnificadoModel", foreign_keys=[pedido_id], back_populates="transacoes", overlaps="pedido")

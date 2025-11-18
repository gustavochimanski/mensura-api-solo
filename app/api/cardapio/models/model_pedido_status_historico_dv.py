from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SAEnum, String, func, Index, Text
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from .model_pedido_dv import PedidoStatus

class PedidoStatusHistoricoModel(Base):
    __tablename__ = "pedido_status_historico_dv"
    __table_args__ = (
        Index("idx_hist_pedido", "pedido_id"),
        Index("idx_hist_status", "status"),
        Index("idx_hist_criado_em", "criado_em"),
        Index("idx_hist_pedido_status", "pedido_id", "status"),
        Index("idx_hist_pedido_criado_em", "pedido_id", "criado_em"),
        {"schema": "cardapio"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("cardapio.pedidos_dv.id", ondelete="CASCADE"), nullable=False)
    status = Column(PedidoStatus, nullable=False)
    motivo = Column(Text, nullable=True)  # Mudança para Text para permitir motivos mais longos
    observacoes = Column(Text, nullable=True)  # Campo adicional para observações detalhadas

    criado_em = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    criado_por_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="SET NULL"), nullable=True)
    ip_origem = Column(String(45), nullable=True)  # IP de origem da mudança (IPv4/IPv6)
    user_agent = Column(String(500), nullable=True)  # User agent do cliente

    pedido = relationship("PedidoDeliveryModel", back_populates="historicos")
    criado_por = relationship("UserModel", foreign_keys=[criado_por_id])

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SAEnum, String, func, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from .model_pedido_dv import PedidoStatus

class PedidoStatusHistoricoModel(Base):
    __tablename__ = "pedido_status_historico_dv"
    __table_args__ = (
        Index("idx_hist_pedido", "pedido_id"),
        {"schema": "delivery"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("delivery.pedidos_dv.id", ondelete="CASCADE"), nullable=False)
    status = Column(PedidoStatus, nullable=False)
    motivo = Column(String(255), nullable=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por = Column(String(60), nullable=True)  # user/system id

    pedido = relationship("PedidoDeliveryModel", back_populates="historicos")

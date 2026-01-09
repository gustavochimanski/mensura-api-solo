# app/api/pedidos/models/model_pedido_historico.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum, Index
from sqlalchemy.orm import relationship

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from .model_pedido import StatusPedidoEnum


class PedidoHistoricoModel(Base):
    """Modelo de histórico de mudanças de status do pedido."""
    __tablename__ = "pedidos_historico"
    __table_args__ = (
        Index("idx_pedidos_historico_pedido", "pedido_id"),
        Index("idx_pedidos_historico_status_novo", "status_novo"),
        Index("idx_pedidos_historico_created_at", "created_at"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    pedido_id = Column(Integer, ForeignKey("pedidos.pedidos.id", ondelete="CASCADE"), nullable=False)
    pedido = relationship("PedidoModel", back_populates="historico")
    
    # Status anterior e novo
    status_anterior = Column(StatusPedidoEnum, nullable=True)
    status_novo = Column(StatusPedidoEnum, nullable=False)
    
    # Usuário que fez a alteração
    usuario_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario = relationship("UserModel", lazy="select")
    
    # Observações sobre a mudança
    observacao = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)


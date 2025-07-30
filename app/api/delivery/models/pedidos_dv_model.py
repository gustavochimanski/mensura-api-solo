from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from datetime import datetime
from pydantic import ConfigDict

class PedidoDeliveryModel(Base):
    __tablename__ = "pedidos_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    cliente_id = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="SET NULL"))
    empresa_id = Column(Integer, ForeignKey("mensura.empresas.id", ondelete="RESTRICT"), nullable=False)

    status = Column(String(2), nullable=False, default="P")  # Ex: P, E, F, C
    valor_total = Column(Numeric(18, 2), nullable=False)
    data_criacao = Column(DateTime, default=datetime.now)

    cliente = relationship("ClienteDeliveryModel", back_populates="pedidos")
    empresa = relationship("EmpresaModel", back_populates="pedidos")
    itens = relationship("PedidoItemModel", back_populates="pedido", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)


from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from datetime import datetime
from pydantic import ConfigDict

class PedidoDeliveryModel(Base):
    __tablename__ = "pedidos_dv"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    cliente_id = Column(Integer, ForeignKey("mensura.clientes_dv.id"), ondelete="SET NULL")
    empresa_id = Column(Integer, ForeignKey("mensura"), ondelete="SET NULL")

    model_config = ConfigDict(from_attributes=True)

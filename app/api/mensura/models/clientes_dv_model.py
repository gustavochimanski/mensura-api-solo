from sqlalchemy import Column, Integer, String, Date, Boolean
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

class ClienteDeliveryModel(Base):
    __tablename__ = "clientes_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    telefone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True)

    pedidos = relationship("PedidoDeliveryModel", back_populates="cliente")

    model_config = ConfigDict(from_attributes=True)


from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class EnderecoDeliveryModel(Base):
    __tablename__ = "enderecos_dv"
    __table_args__ = {"schema": "delivery"}

    id          = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id  = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="CASCADE"), nullable=False)

    cep         = Column(String(10),  nullable=True)
    logradouro  = Column(String(100), nullable=True)
    numero      = Column(String(10),  nullable=True)
    complemento = Column(String(50),  nullable=True)
    bairro      = Column(String(50),  nullable=True)
    cidade      = Column(String(50),  nullable=True)
    estado      = Column(String(2),   nullable=True)

    # Relação N:1 com ClienteDeliveryModel
    cliente = relationship("ClienteDeliveryModel", back_populates="enderecos")

    model_config = ConfigDict(from_attributes=True)

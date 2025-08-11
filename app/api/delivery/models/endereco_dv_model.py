from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Numeric, Boolean
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

    # apoio ao delivery
    ponto_referencia = Column(String(120), nullable=True)
    latitude   = Column(Numeric(10, 6), nullable=True)
    longitude  = Column(Numeric(10, 6), nullable=True)
    is_principal = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    cliente = relationship("ClienteDeliveryModel", back_populates="enderecos")
    pedidos = relationship("PedidoDeliveryModel", back_populates="endereco", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)

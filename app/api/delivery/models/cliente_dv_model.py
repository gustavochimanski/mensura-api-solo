from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, func, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

class ClienteDeliveryModel(Base):
    __tablename__ = "clientes_dv"
    __table_args__ = (
        Index("idx_clientes_cpf", "cpf"),
        Index("idx_clientes_email", "email"),
        {"schema": "delivery"},
    )

    telefone = Column(Integer, primary_key=True)  # PK principal
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pedidos = relationship("PedidoDeliveryModel", back_populates="cliente")
    enderecos = relationship("EnderecoDeliveryModel", back_populates="cliente", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)
#
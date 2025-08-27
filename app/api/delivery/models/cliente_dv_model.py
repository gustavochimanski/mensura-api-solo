import base64
import hashlib
import secrets

from sqlalchemy import Column, String, Date, Boolean, DateTime, func, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

def default_super_token():
    raw = secrets.token_bytes(32)
    hashed = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(hashed).rstrip(b'=').decode('ascii')

class ClienteDeliveryModel(Base):
    __tablename__ = "clientes_dv"
    __table_args__ = (
        Index("idx_clientes_cpf", "cpf"),
        Index("idx_clientes_email", "email"),
        {"schema": "delivery"},
    )

    telefone = Column(String(20), primary_key=True)  # PK principal
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    super_token = Column(String, unique=True, nullable=False, default=default_super_token)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pedidos = relationship(
        "PedidoDeliveryModel",
        back_populates="cliente",
        cascade="all, delete-orphan",
        foreign_keys="PedidoDeliveryModel.cliente_telefone"  # especifica a FK correta
    )

    enderecos = relationship("EnderecoDeliveryModel", back_populates="cliente", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)
#
import base64
import hashlib
import secrets

from sqlalchemy import Column, String, Date, Boolean, DateTime, func, Index, Integer
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

from app.utils.database_utils import now_trimmed


def default_super_token():
    raw = secrets.token_bytes(32)
    hashed = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(hashed).rstrip(b'=').decode('ascii')


class ClienteModel(Base):
    __tablename__ = "clientes"
    __table_args__ = (
        Index("idx_clientes_cpf", "cpf"),
        Index("idx_clientes_email", "email"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)  # PK interna e imutável
    telefone = Column(String(20), nullable=False, unique=True)  # telefone é só um dado mutável
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    super_token = Column(String, unique=True, nullable=False, default=default_super_token)

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    # Relacionamentos usando cliente_id como FK
    pedidos = relationship(
        "PedidoUnificadoModel",
        back_populates="cliente",
        cascade="all, delete-orphan",
        foreign_keys="PedidoUnificadoModel.cliente_id"  # referencia id do cliente
    )

    enderecos = relationship(
        "EnderecoModel",
        back_populates="cliente",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)

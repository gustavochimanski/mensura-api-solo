# app/api/mensura/models/empresa_model.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import ConfigDict

from app.api.mensura.models.association_tables import entregador_empresa, usuario_empresa
from app.database.db_connection import Base


class EmpresaModel(Base):
    __tablename__ = "empresas"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(20), nullable=True, unique=True)
    slug = Column(String(50), nullable=False, unique=True)
    logo = Column(String(255), nullable=True)

    endereco_id = Column(
        Integer,
        ForeignKey("mensura.enderecos.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Relationships
    produtos_emp = relationship("ProdutoEmpModel", back_populates="empresa")
    pedidos = relationship("PedidoDeliveryModel", back_populates="empresa", cascade="all, delete-orphan")
    entregadores = relationship("EntregadorDeliveryModel", secondary=entregador_empresa, back_populates="empresas")
    usuarios = relationship("UserModel", secondary=usuario_empresa, back_populates="empresas")
    endereco = relationship("EnderecoModel", back_populates="empresa")

    model_config = ConfigDict(from_attributes=True)

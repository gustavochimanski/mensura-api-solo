# app/models/mensura/empresa.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict


class EmpresaModel(Base):
    __tablename__ = "empresas"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(20), nullable=True, unique=True)
    slug = Column(String(50), nullable=False, unique=True)
    logo = Column(String(255), nullable=True)

    # Relacionamentos (reversos)
    produtos = relationship("ProdutosEmpDeliveryModel", back_populates="empresa_rel")
    sub_categorias = relationship("SubCategoriaModel", back_populates="empresa_rel")

    model_config = ConfigDict(from_attributes=True)

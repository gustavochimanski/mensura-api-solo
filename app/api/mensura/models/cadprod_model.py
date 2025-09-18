from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, Numeric, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.api.mensura.models.categoria_model import CategoriaModel
    from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel

class ProdutoModel(Base):
    __tablename__ = "cadprod"
    __table_args__ = {"schema": "mensura"}

    cod_barras = Column(String, primary_key=True, unique=True, nullable=False)
    descricao = Column(String(255), nullable=False)
    imagem = Column(String(255), nullable=True)
    data_cadastro = Column(Date, nullable=True)
    cod_categoria = Column(Integer, ForeignKey("mensura.categorias.id", ondelete="RESTRICT"), nullable=True)

    # extras úteis para cardápio
    ativo = Column(Boolean, nullable=False, default=True)
    unidade_medida = Column(String(10), nullable=True)  # ex: "UN", "KG"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    categoria = relationship("CategoriaModel", back_populates="produtos", lazy="select")
    produtos_empresa = relationship("ProdutoEmpModel", back_populates="produto", cascade="all, delete-orphan", lazy="select")

    model_config = ConfigDict(from_attributes=True)

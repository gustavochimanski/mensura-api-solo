from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, Numeric, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutoDeliveryModel(Base):
    __tablename__ = "cadprod_dv"
    __table_args__ = {"schema": "delivery"}

    cod_barras = Column(String, primary_key=True, unique=True, nullable=False)
    descricao = Column(String(255), nullable=False)
    imagem = Column(String(255), nullable=True)
    data_cadastro = Column(Date, nullable=True)
    cod_categoria = Column(Integer, ForeignKey("delivery.categoria_dv.id", ondelete="RESTRICT"), nullable=False)

    # extras úteis para cardápio
    ativo = Column(Boolean, nullable=False, default=True)
    unidade_medida = Column(String(10), nullable=True)  # ex: "UN", "KG"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    categoria = relationship("CategoriaDeliveryModel", back_populates="produtos")
    produtos_empresa = relationship("ProdutoEmpDeliveryModel", back_populates="produto", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)

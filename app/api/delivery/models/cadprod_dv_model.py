from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Date, ForeignKey
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

    # Relacionamentos
    categoria = relationship("CategoriaDeliveryModel", back_populates="produtos")

    # Produtos associados às empresas
    produtos_empresa = relationship("ProdutoEmpDeliveryModel", back_populates="produto", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)

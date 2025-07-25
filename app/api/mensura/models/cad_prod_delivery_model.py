from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutoDeliveryModel(Base):
    __tablename__ = "cadprod_delivery"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True)
    cod_barras = Column(String, nullable=False, unique=True)
    descricao = Column(String(255), nullable=False)
    imagem = Column(String(255), nullable=True)
    data_cadastro = Column(Date, nullable=True)

    cod_categoria = Column(
        Integer,
        ForeignKey("mensura.categoria_delivery.id", ondelete="RESTRICT"),
        nullable=False
    )
    categoria = relationship(
        "CategoriaDeliveryModel",
        back_populates="produtos"
    )

    # Produtos associados às empresas
    produtos_empresa = relationship(
        "ProdutosEmpDeliveryModel",
        back_populates="produto",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)

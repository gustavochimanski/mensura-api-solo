from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class ProdutoDeliveryModel(Base):
    __tablename__ = "cadprod_dv"
    __table_args__ = {"schema": "delivery"}

    cod_barras = Column(String, nullable=False, unique=True, primary_key=True)
    descricao = Column(String(255), nullable=False)
    imagem = Column(String(255), nullable=True)
    data_cadastro = Column(Date, nullable=True)

    cod_categoria = Column(
        Integer,
        ForeignKey("mensura.categoria_dv.id", ondelete="RESTRICT"),
        nullable=False
    )
    categoria = relationship(
        "CategoriaDeliveryModel",
        back_populates="produtos"
    )

    # Produtos associados às empresass
    produtos_empresa = relationship(
        "ProdutosEmpDeliveryModel",
        back_populates="produto",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)

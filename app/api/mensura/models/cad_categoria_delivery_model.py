from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.database.db_connection import Base

class CategoriaDeliveryModel(Base):
    __tablename__ = "categoria_delivery"
    __table_args__ = {"schema": "mensura"}

    id = Column(Integer, primary_key=True)
    descricao = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    slug_pai = Column(String(100), nullable=True)
    imagem = Column(String(255), nullable=True)
    posicao = Column(Integer, nullable=True)

    produtos = relationship(
        "ProdutoDeliveryModel",
        back_populates="categoria"
    )
    sub_categorias = relationship(
        "SubCategoriaModel",
        back_populates="categoria"
    )

    @hybrid_property
    def label(self) -> str:
        return self.descricao

    @hybrid_property
    def href(self) -> str:
        return f"/categoria/{self.slug}"

    model_config = ConfigDict(from_attributes=True)

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.database.db_connection import Base

class CategoriaDeliveryModel(Base):
    __tablename__ = "categoria_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    descricao = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)

    # Self-relation para hierarquia
    parent_id = Column(Integer, ForeignKey("delivery.categoria_dv.id"), nullable=True)
    parent = relationship(
        "CategoriaDeliveryModel",
        remote_side=[id],
        back_populates="children"
    )
    children    = relationship(
        "CategoriaDeliveryModel",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    imagem = Column(String(255), nullable=True)
    posicao = Column(Integer, nullable=False)

    produtos = relationship("ProdutoDeliveryModel", back_populates="categoria")
    vitrines_dv = relationship("VitrinesModel", back_populates="categoria")

    @hybrid_property
    def href(self) -> str:
        return f"/categorias/{self.slug}"

from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.database.db_connection import Base

class CategoriaDeliveryModel(Base):
    __tablename__ = "categoria_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    descricao = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)

    # "P" = aparece na home, outros valores = não aparece
    tipo_exibicao = Column(String(1), nullable=True)

    parent_id = Column(Integer, ForeignKey("delivery.categoria_dv.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("CategoriaDeliveryModel", remote_side=[id], back_populates="children")
    children = relationship("CategoriaDeliveryModel", back_populates="parent", cascade="all, delete-orphan")

    imagem = Column(String(255), nullable=True)
    posicao = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    produtos = relationship("ProdutoDeliveryModel", back_populates="categoria")
    vitrines_dv = relationship("VitrinesModel", back_populates="categoria")

    @hybrid_property
    def href(self) -> str:
        return f"/categorias/{self.slug}"

    @hybrid_property
    def slug_pai(self) -> Optional[str]:
        return self.parent.slug if self.parent else None

    @property
    def label(self) -> str:
        return self.descricao

    @hybrid_property
    def is_home(self) -> bool:
        """Retorna True se a categoria deve aparecer na home."""
        return self.tipo_exibicao == "P"

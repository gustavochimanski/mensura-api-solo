# app/api/delivery/models/model_categoria_dv.py
from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.api.mensura.models.association_tables import VitrineCategoriaLink
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class CategoriaDeliveryModel(Base):
    __tablename__ = "categoria_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True)
    descricao = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)

    parent_id = Column(Integer, ForeignKey("delivery.categoria_dv.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("CategoriaDeliveryModel", remote_side=[id], back_populates="children")
    children = relationship("CategoriaDeliveryModel", back_populates="parent", cascade="all, delete-orphan")

    imagem = Column(String(255), nullable=True)
    posicao = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    produtos = relationship("ProdutoModel", back_populates="categoria")

    # --- N:N com vitrines ---
    vitrines = relationship(
        "VitrinesModel",
        secondary=VitrineCategoriaLink.__table__,
        back_populates="categorias",
        passive_deletes=True,
        order_by=VitrineCategoriaLink.posicao,
    )

    @hybrid_property
    def href(self) -> str:
        return f"/categorias/{self.slug}"

    @hybrid_property
    def slug_pai(self) -> Optional[str]:
        return self.parent.slug if self.parent else None

    @property
    def label(self) -> str:
        return self.descricao

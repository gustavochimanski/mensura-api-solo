from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.api.cadastros.models.association_tables import VitrineCategoriaLink
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class CategoriaDeliveryModel(Base):
    __tablename__ = "categoria_dv"
    __table_args__ = (
        UniqueConstraint("empresa_id", "slug", name="uq_categoria_slug_empresa"),
        {"schema": "cardapio"},
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), nullable=True, index=True)
    descricao = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)

    parent_id = Column(Integer, ForeignKey("cardapio.categoria_dv.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("CategoriaDeliveryModel", remote_side=[id], back_populates="children")
    children = relationship("CategoriaDeliveryModel", back_populates="parent", cascade="all, delete-orphan")

    imagem = Column(String(255), nullable=True)
    posicao = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    # --- N:N com vitrines ---
    vitrines = relationship(
        "VitrinesModel",
        secondary=VitrineCategoriaLink.__table__,
        back_populates="categorias",
        passive_deletes=True,
        order_by=VitrineCategoriaLink.posicao,
    )

    banners = relationship("BannerParceiroModel", back_populates="categoria")
#
    @hybrid_property
    def href(self) -> str:
        partes = []
        atual = self
        while atual is not None:
            partes.append(atual.slug)
            atual = atual.parent
        partes.reverse()
        caminho = "/".join(partes)
        return f"/cardapio/categoria/{caminho}"

    @hybrid_property
    def slug_pai(self) -> Optional[str]:
        return self.parent.slug if self.parent else None

    @property
    def label(self) -> str:
        return self.descricao

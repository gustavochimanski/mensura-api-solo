from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.api.cadastros.models.association_tables import (
    VitrineCategoriaLink, 
    VitrineProdutoLink,
    VitrineComboLink,
    VitrineReceitaLink,
    VitrineLandingProdutoLink,
    VitrineLandingComboLink,
    VitrineLandingReceitaLink,
)
from app.database.db_connection import Base

class VitrinesModel(Base):
    __tablename__ = "vitrines_dv"
    __table_args__ = (
        UniqueConstraint("empresa_id", "slug", name="uq_vitrine_slug_empresa"),
        {"schema": "cardapio"},
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), nullable=True, index=True)
    tipo_exibicao = Column(String(1), nullable=True)
    titulo = Column(String(100), nullable=False)
    slug   = Column(String(100), nullable=False)  # unique por empresa via table_args
    ordem  = Column(Integer, nullable=False, default=1)
    # --- Relacionamentos N:N ---
    categorias = relationship(
        "CategoriaDeliveryModel",
        secondary=VitrineCategoriaLink.__table__,
        back_populates="vitrines",
        passive_deletes=True,
        order_by=VitrineCategoriaLink.posicao,
    )

    produtos = relationship(
        "ProdutoModel",
        secondary=VitrineProdutoLink.__table__,
        back_populates="vitrines",
        passive_deletes=True
    )

    combos = relationship(
        "ComboModel",
        secondary=VitrineComboLink.__table__,
        passive_deletes=True,
        order_by=VitrineComboLink.posicao,
    )

    receitas = relationship(
        "ReceitaModel",
        secondary=VitrineReceitaLink.__table__,
        order_by=VitrineReceitaLink.posicao,
        viewonly=True,
    )

    @hybrid_property
    def is_home(self) -> bool:
        return self.tipo_exibicao == "P"


class VitrinesLandingpageStoreModel(Base):
    """
    Vitrines para landing page da store (sem vínculo com categoria).
    """
    __tablename__ = "vitrines_landingpage_store"
    __table_args__ = (
        UniqueConstraint("empresa_id", "slug", name="uq_vitrine_landing_slug_empresa"),
        {"schema": "cardapio"},
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), nullable=True, index=True)
    tipo_exibicao = Column(String(1), nullable=True)
    titulo = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    ordem = Column(Integer, nullable=False, default=1)

    produtos = relationship(
        "ProdutoModel",
        secondary=VitrineLandingProdutoLink.__table__,
        passive_deletes=True,
    )

    combos = relationship(
        "ComboModel",
        secondary=VitrineLandingComboLink.__table__,
        passive_deletes=True,
        order_by=VitrineLandingComboLink.posicao,
    )

    receitas = relationship(
        "ReceitaModel",
        secondary=VitrineLandingReceitaLink.__table__,
        order_by=VitrineLandingReceitaLink.posicao,
        viewonly=True,
    )

    @hybrid_property
    def is_home(self) -> bool:
        return self.tipo_exibicao == "P"

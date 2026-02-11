from __future__ import annotations

from pydantic import ConfigDict
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Boolean,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class ComboSecaoModel(Base):
    """
    Seção de um combo — agrupa itens e define regras de seleção (obrigatório, min/max).
    """
    __tablename__ = "combo_secoes"
    __table_args__ = ({"schema": "catalogo"},)

    id = Column(Integer, primary_key=True, autoincrement=True)
    combo_id = Column(Integer, ForeignKey("catalogo.combos.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo = Column(String(120), nullable=False)
    descricao = Column(String(255), nullable=True)

    # Regras da seção
    obrigatorio = Column(Boolean, nullable=False, default=False)
    quantitativo = Column(Boolean, nullable=False, default=False)
    minimo_itens = Column(Integer, nullable=False, default=0)
    maximo_itens = Column(Integer, nullable=False, default=1)
    ordem = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    combo = relationship("ComboModel", back_populates="secoes")
    itens = relationship(
        "ComboSecaoItemModel",
        back_populates="secao",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    model_config = ConfigDict(from_attributes=True)


class ComboSecaoItemModel(Base):
    """
    Item vinculado a uma seção de combo.
    Aceita produto (FK) ou receita (FK). Define preco_incremental (pode ser 0),
    e se permite quantidade por item.
    """
    __tablename__ = "combo_secoes_itens"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN (produto_id IS NOT NULL OR produto_cod_barras IS NOT NULL) THEN 1 ELSE 0 END + "
            "CASE WHEN receita_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_combo_secao_item_exatamente_um_tipo",
        ),
        {"schema": "catalogo"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    secao_id = Column(Integer, ForeignKey("catalogo.combo_secoes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Exatamente um desses campos deve ser preenchido
    produto_id = Column(Integer, ForeignKey("catalogo.produtos.id", ondelete="RESTRICT"), nullable=True, index=True)
    produto_cod_barras = Column(String, nullable=True, index=True)
    receita_id = Column(Integer, ForeignKey("catalogo.receitas.id", ondelete="RESTRICT"), nullable=True, index=True)

    ordem = Column(Integer, nullable=False, default=0)

    # Preço incremental aplicado quando este item é selecionado (pode ser zero)
    preco_incremental = Column(Numeric(18, 2), nullable=False, default=0)

    # Permite o cliente escolher quantidade deste item dentro da seção
    permite_quantidade = Column(Boolean, nullable=False, default=False)
    quantidade_min = Column(Integer, nullable=False, default=1)
    quantidade_max = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    secao = relationship("ComboSecaoModel", back_populates="itens")
    produto = relationship("ProdutoModel", foreign_keys=[produto_id])
    receita = relationship("ReceitaModel", foreign_keys=[receita_id])

    model_config = ConfigDict(from_attributes=True)

    @property
    def nome(self) -> str | None:
        if self.produto is not None:
            return getattr(self.produto, "descricao", None)
        if self.receita is not None:
            return getattr(self.receita, "nome", None)
        return None

    @property
    def imagem(self) -> str | None:
        if self.produto is not None:
            return getattr(self.produto, "imagem", None)
        if self.receita is not None:
            return getattr(self.receita, "imagem", None)
        return None


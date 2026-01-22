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
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class ComplementoVinculoItemModel(Base):
    """
    Vínculo de um item (produto/receita/combo) dentro de um complemento.

    IMPORTANTE:
    - Esta tabela substitui o conceito antigo de `catalogo.adicionais`.
    - No retorno da API, esse vínculo continua sendo exposto como `adicionais` para o front,
      mantendo nome/estrutura, porém o ID agora identifica o vínculo (row) e não mais um
      cadastro independente de adicional.
    """

    __tablename__ = "complemento_vinculo_item"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN produto_cod_barras IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN receita_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN combo_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_complemento_vinculo_item_exatamente_um_tipo",
        ),
        Index("uq_comp_vinc_produto", "complemento_id", "produto_cod_barras", unique=True,
              postgresql_where=text("produto_cod_barras IS NOT NULL")),
        Index("uq_comp_vinc_receita", "complemento_id", "receita_id", unique=True,
              postgresql_where=text("receita_id IS NOT NULL")),
        Index("uq_comp_vinc_combo", "complemento_id", "combo_id", unique=True,
              postgresql_where=text("combo_id IS NOT NULL")),
        {"schema": "catalogo"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    complemento_id = Column(
        Integer,
        ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Exatamente um desses 3 campos deve estar preenchido
    produto_cod_barras = Column(
        String,
        ForeignKey("catalogo.produtos.cod_barras", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    receita_id = Column(
        Integer,
        ForeignKey("catalogo.receitas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    combo_id = Column(
        Integer,
        ForeignKey("catalogo.combos.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    ordem = Column(Integer, nullable=False, default=0)

    # Valor do adicional neste complemento. Quando preenchido, define o preço exibido/calculado
    # para o "adicional"; caso contrário, usa o preço da entidade (produto_emp, receita, combo).
    preco_complemento = Column(Numeric(18, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    complemento = relationship("ComplementoModel", back_populates="vinculos_itens")
    produto = relationship("ProdutoModel", foreign_keys=[produto_cod_barras])
    receita = relationship("ReceitaModel", foreign_keys=[receita_id])
    combo = relationship("ComboModel", foreign_keys=[combo_id])

    model_config = ConfigDict(from_attributes=True)

    # ---- Propriedades compatíveis (usadas em snapshots/serialização) ----
    @property
    def nome(self) -> str | None:
        if self.produto is not None:
            return getattr(self.produto, "descricao", None)
        if self.receita is not None:
            return getattr(self.receita, "nome", None)
        if self.combo is not None:
            return getattr(self.combo, "titulo", None) or getattr(self.combo, "descricao", None)
        return None

    @property
    def descricao(self) -> str | None:
        if self.produto is not None:
            # Produto não tem "nome" separado; usa o descritivo como nome.
            return None
        if self.receita is not None:
            return getattr(self.receita, "descricao", None)
        if self.combo is not None:
            return getattr(self.combo, "descricao", None)
        return None

    @property
    def imagem(self) -> str | None:
        if self.produto is not None:
            return getattr(self.produto, "imagem", None)
        if self.receita is not None:
            return getattr(self.receita, "imagem", None)
        if self.combo is not None:
            return getattr(self.combo, "imagem", None)
        return None

    @property
    def ativo(self) -> bool:
        if self.produto is not None:
            return bool(getattr(self.produto, "ativo", True))
        if self.receita is not None:
            return bool(getattr(self.receita, "ativo", True))
        if self.combo is not None:
            return bool(getattr(self.combo, "ativo", True))
        return True


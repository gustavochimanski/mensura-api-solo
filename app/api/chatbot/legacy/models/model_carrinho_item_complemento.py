from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class CarrinhoItemComplementoModel(Base):
    """
    Complementos selecionados para um item do carrinho temporário (produto/receita/combo).

    Estrutura similar a pedidos_itens_complementos, mas para carrinho temporário.
    """

    __tablename__ = "carrinho_itens_complementos"
    __table_args__ = (
        Index("idx_carrinho_itens_complementos_item", "carrinho_item_id"),
        Index("idx_carrinho_itens_complementos_complemento", "complemento_id"),
        {"schema": "chatbot"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    carrinho_item_id = Column(
        Integer,
        ForeignKey("chatbot.carrinho_itens.id", ondelete="CASCADE"),
        nullable=False,
    )
    carrinho_item = relationship("CarrinhoItemModel", back_populates="complementos")

    # Referência ao complemento do catálogo
    complemento_id = Column(
        Integer,
        ForeignKey("catalogo.complemento_produto.id", ondelete="RESTRICT"),
        nullable=False,
    )
    complemento = relationship("ComplementoModel", lazy="select")

    # Total deste complemento (soma dos adicionais considerando quantidade do item)
    total = Column(Numeric(18, 2), nullable=False, default=0)

    adicionais = relationship(
        "CarrinhoItemComplementoAdicionalModel",
        back_populates="item_complemento",
        cascade="all, delete-orphan",
        lazy="select"
    )

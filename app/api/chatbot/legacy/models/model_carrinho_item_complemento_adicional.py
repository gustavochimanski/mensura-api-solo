from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class CarrinhoItemComplementoAdicionalModel(Base):
    """
    Adicionais selecionados dentro de um complemento de um item do carrinho temporário.
    
    Estrutura similar a pedidos_itens_complementos_adicionais, mas para carrinho temporário.
    """

    __tablename__ = "carrinho_itens_complementos_adicionais"
    __table_args__ = (
        Index("idx_carrinho_itens_comp_adic_item_comp", "item_complemento_id"),
        Index("idx_carrinho_itens_comp_adic_adicional", "adicional_id"),
        {"schema": "chatbot"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    item_complemento_id = Column(
        Integer,
        ForeignKey("chatbot.carrinho_itens_complementos.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_complemento = relationship("CarrinhoItemComplementoModel", back_populates="adicionais")

    adicional_id = Column(
        Integer,
        ForeignKey("catalogo.complemento_vinculo_item.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adicional = relationship("ComplementoVinculoItemModel", lazy="select")

    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False, default=0)
    total = Column(Numeric(18, 2), nullable=False, default=0)

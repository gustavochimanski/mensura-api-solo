from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, Boolean, Index
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class PedidoItemComplementoModel(Base):
    """
    Complementos selecionados para um item do pedido (produto/receita/combo).

    Substitui o antigo campo JSON `adicionais_snapshot` por modelo relacional.
    """

    __tablename__ = "pedidos_itens_complementos"
    __table_args__ = (
        Index("idx_pedidos_itens_complementos_item", "pedido_item_id"),
        Index("idx_pedidos_itens_complementos_complemento", "complemento_id"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    pedido_item_id = Column(
        Integer,
        ForeignKey("pedidos.pedidos_itens.id", ondelete="CASCADE"),
        nullable=False,
    )
    pedido_item = relationship("PedidoItemUnificadoModel", back_populates="complementos")

    # Referência ao complemento do catálogo (opcionalmente útil para auditoria/BI)
    complemento_id = Column(
        Integer,
        ForeignKey("catalogo.complemento_produto.id", ondelete="RESTRICT"),
        nullable=False,
    )
    complemento = relationship("ComplementoModel", lazy="select")

    # Snapshot no momento do pedido (para não “mudar o passado”)
    complemento_nome = Column(String(120), nullable=True)
    obrigatorio = Column(Boolean, nullable=False, default=False)
    quantitativo = Column(Boolean, nullable=False, default=False)

    # Total deste complemento (soma dos adicionais considerando quantidade do item)
    total = Column(Numeric(18, 2), nullable=False, default=0)

    adicionais = relationship(
        "PedidoItemComplementoAdicionalModel",
        back_populates="item_complemento",
        cascade="all, delete-orphan",
    )


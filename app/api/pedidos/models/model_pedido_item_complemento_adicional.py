from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, Index
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class PedidoItemComplementoAdicionalModel(Base):
    """
    Adicionais selecionados dentro de um complemento de um item do pedido.
    """

    __tablename__ = "pedidos_itens_complementos_adicionais"
    __table_args__ = (
        Index("idx_pedidos_itens_comp_adic_item_comp", "item_complemento_id"),
        Index("idx_pedidos_itens_comp_adic_adicional", "adicional_id"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    item_complemento_id = Column(
        Integer,
        ForeignKey("pedidos.pedidos_itens_complementos.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_complemento = relationship("PedidoItemComplementoModel", back_populates="adicionais")

    adicional_id = Column(
        Integer,
        ForeignKey("catalogo.adicionais.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adicional = relationship("AdicionalModel", lazy="select")

    # Snapshot no momento do pedido
    nome = Column(String(120), nullable=True)

    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False, default=0)
    total = Column(Numeric(18, 2), nullable=False, default=0)


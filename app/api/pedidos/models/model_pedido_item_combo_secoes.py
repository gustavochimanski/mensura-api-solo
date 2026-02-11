from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class PedidoItemComboSecaoModel(Base):
    __tablename__ = "pedido_item_combo_secoes"
    __table_args__ = {"schema": "pedidos"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_item_id = Column(Integer, ForeignKey("pedidos.pedidos_itens.id", ondelete="CASCADE"), nullable=False, index=True)
    secao_id = Column(Integer, ForeignKey("catalogo.combo_secoes.id", ondelete="SET NULL"), nullable=True, index=True)
    secao_titulo_snapshot = Column(String(120), nullable=True)
    ordem = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    itens = relationship(
        "PedidoItemComboSecaoItemModel",
        back_populates="secao",
        cascade="all, delete-orphan",
    )

    model_config = ConfigDict(from_attributes=True)


class PedidoItemComboSecaoItemModel(Base):
    __tablename__ = "pedido_item_combo_secoes_itens"
    __table_args__ = {"schema": "pedidos"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_item_secao_id = Column(Integer, ForeignKey("pedidos.pedido_item_combo_secoes.id", ondelete="CASCADE"), nullable=False, index=True)
    combo_secoes_item_id = Column(Integer, ForeignKey("catalogo.combo_secoes_itens.id", ondelete="SET NULL"), nullable=True, index=True)
    produto_cod_barras_snapshot = Column(String, nullable=True)
    receita_id_snapshot = Column(Integer, nullable=True)
    preco_incremental_snapshot = Column(Integer, nullable=False, default=0)
    quantidade = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    secao = relationship("PedidoItemComboSecaoModel", back_populates="itens")

    model_config = ConfigDict(from_attributes=True)


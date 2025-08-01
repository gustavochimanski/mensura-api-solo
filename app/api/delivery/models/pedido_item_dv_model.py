from sqlalchemy import Column, Integer, ForeignKey, String, Numeric
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

class PedidoItemModel(Base):
    __tablename__ = "pedido_itens_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("delivery.pedidos_dv.id", ondelete="CASCADE"), nullable=False)
    produto_cod_barras = Column(String, ForeignKey("delivery.cadprod_dv.cod_barras", ondelete="RESTRICT"), nullable=False)

    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False)

    pedido = relationship("PedidoDeliveryModel", back_populates="itens")
    produto = relationship("ProdutoDeliveryModel")

    model_config = ConfigDict(from_attributes=True)

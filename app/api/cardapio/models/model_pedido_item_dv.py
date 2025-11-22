from pydantic import ConfigDict
from sqlalchemy import Column, Integer, ForeignKey, String, Numeric, JSON
from sqlalchemy.orm import relationship
from app.database.db_connection import Base

class PedidoItemModel(Base):
    __tablename__ = "pedido_itens_dv"
    __table_args__ = {"schema": "cardapio"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("cardapio.pedidos_dv.id", ondelete="CASCADE"), nullable=False)
    produto_cod_barras = Column(String, ForeignKey("catalogo.produtos.cod_barras", ondelete="RESTRICT"), nullable=False)

    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False)
    observacao = Column(String(255), nullable=True)

    # snapshots para não “mudar o passado” se o produto for atualizado
    produto_descricao_snapshot = Column(String(255), nullable=True)
    produto_imagem_snapshot = Column(String(255), nullable=True)
    adicionais_snapshot = Column(JSON, nullable=True)

    pedido = relationship("PedidoDeliveryModel", back_populates="itens")
    produto = relationship("ProdutoModel")

    model_config = ConfigDict(from_attributes=True)

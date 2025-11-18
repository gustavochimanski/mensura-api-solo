# app/api/balcao/models/model_pedido_balcao_item.py
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class PedidoBalcaoItemModel(Base):
    __tablename__ = "pedido_balcao_itens"
    __table_args__ = {"schema": "balcao"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("balcao.pedidos_balcao.id", ondelete="CASCADE"), nullable=False)
    produto_cod_barras = Column(String, ForeignKey("catalogo.produtos.cod_barras", ondelete="RESTRICT"), nullable=False)
    
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False)
    observacao = Column(String(255), nullable=True)
    
    # Snapshots para não "mudar o passado" se o produto for atualizado
    produto_descricao_snapshot = Column(String(255), nullable=True)
    produto_imagem_snapshot = Column(String(255), nullable=True)
    
    # Relacionamentos
    pedido = relationship("PedidoBalcaoModel", back_populates="itens")
    produto = relationship("ProdutoModel")


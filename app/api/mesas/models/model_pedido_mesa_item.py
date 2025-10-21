# app/api/mesas/models/model_pedido_mesa_item.py
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class PedidoMesaItemModel(Base):
    __tablename__ = "pedido_mesa_itens"
    __table_args__ = {"schema": "mesas"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    pedido_id = Column(Integer, ForeignKey("mesas.pedidos_mesa.id", ondelete="CASCADE"), nullable=False)
    produto_cod_barras = Column(String, ForeignKey("mensura.cadprod.cod_barras", ondelete="RESTRICT"), nullable=False)
    
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False)
    observacao = Column(String(255), nullable=True)
    
    # Snapshots para não "mudar o passado" se o produto for atualizado
    produto_descricao_snapshot = Column(String(255), nullable=True)
    produto_imagem_snapshot = Column(String(255), nullable=True)
    
    # Relacionamentos
    pedido = relationship("PedidoMesaModel", back_populates="itens")
    produto = relationship("ProdutoModel")

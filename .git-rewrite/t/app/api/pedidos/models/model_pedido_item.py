# app/api/pedidos/models/model_pedido_item.py
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text, Index
from sqlalchemy.orm import relationship

from app.database.db_connection import Base


class PedidoUnificadoItemModel(Base):
    """Modelo de item de pedido unificado."""
    __tablename__ = "pedidos_itens"
    __table_args__ = (
        Index("idx_pedidos_itens_pedido", "pedido_id"),
        {"schema": "pedidos"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    pedido_id = Column(Integer, ForeignKey("pedidos.pedidos.id", ondelete="CASCADE"), nullable=False)
    pedido = relationship("PedidoModel", back_populates="itens")
    
    # Identificação do item
    produto_cod_barras = Column(String, ForeignKey("catalogo.produtos.cod_barras", ondelete="SET NULL"), nullable=True)
    produto = relationship("ProdutoModel", lazy="select")
    
    combo_id = Column(Integer, ForeignKey("catalogo.combos.id", ondelete="SET NULL"), nullable=True)
    combo = relationship("ComboModel", lazy="select")
    
    # Dados do item
    nome = Column(String(255), nullable=False)  # Snapshot do nome no momento do pedido
    descricao = Column(Text, nullable=True)
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False)
    preco_total = Column(Numeric(18, 2), nullable=False)
    
    # Observações específicas do item
    observacoes = Column(String(500), nullable=True)
    
    # Snapshot dos adicionais (JSON)
    adicionais = Column(Text, nullable=True)  # JSON serializado dos adicionais selecionados


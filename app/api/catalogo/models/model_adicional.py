
from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class AdicionalModel(Base):
    """Modelo para itens de complementos (ex: molhos, tamanhos de bebida, etc.)"""
    __tablename__ = "complemento_itens"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Vinculado a uma empresa
    empresa_id = Column(Integer, nullable=False, index=True)  # Sem FK para evitar dependência circular
    
    # Vinculado a um complemento (grupo de itens)
    complemento_id = Column(Integer, ForeignKey("catalogo.complemento_produto.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Informações do adicional
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    preco = Column(Numeric(18, 2), nullable=False, default=0)
    custo = Column(Numeric(18, 2), nullable=False, default=0)  # Custo interno do adicional
    
    # Configurações
    ativo = Column(Boolean, nullable=False, default=True)
    
    # Ordem de exibição dentro do complemento
    ordem = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento com complemento
    complemento = relationship(
        "ComplementoModel",
        back_populates="adicionais",
    )
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<Adicional(id={self.id}, nome='{self.nome}', empresa={self.empresa_id})>"


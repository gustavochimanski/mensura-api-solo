from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class AdicionalModel(Base):
    """Modelo para adicionais de produtos (ex: molhos, tamanhos de bebida, etc.)"""
    __tablename__ = "adicional_produto"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Vinculado a uma empresa
    empresa_id = Column(Integer, nullable=False, index=True)  # Sem FK para evitar dependência circular
    
    # Informações do adicional
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    preco = Column(Numeric(18, 2), nullable=False, default=0)
    
    # Configurações
    ativo = Column(Boolean, nullable=False, default=True)
    obrigatorio = Column(Boolean, nullable=False, default=False)  # Se o adicional é obrigatório
    permite_multipla_escolha = Column(Boolean, nullable=False, default=True)  # Se pode escolher múltiplos
    
    # Ordem de exibição
    ordem = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento N:N com produtos
    produtos = relationship(
        "ProdutoModel",
        secondary="catalogo.produto_adicional_link",
        back_populates="adicionais",
        viewonly=True,  # Leitura apenas, pois a relação real é no link
    )
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<Adicional(id={self.id}, nome='{self.nome}', empresa={self.empresa_id})>"


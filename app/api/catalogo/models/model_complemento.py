from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class ComplementoModel(Base):
    """Modelo para complementos de produtos (grupos de itens com configurações)"""
    __tablename__ = "complemento_produto"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Vinculado a uma empresa
    empresa_id = Column(Integer, nullable=False, index=True)  # Sem FK para evitar dependência circular
    
    # Informações do complemento
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    
    # Configurações do complemento
    ativo = Column(Boolean, nullable=False, default=True)
    obrigatorio = Column(Boolean, nullable=False, default=False)  # Se o complemento é obrigatório
    quantitativo = Column(Boolean, nullable=False, default=False)  # Se permite quantidade (ex: 2x bacon)
    permite_multipla_escolha = Column(Boolean, nullable=False, default=True)  # Se pode escolher múltiplos adicionais
    
    # Ordem de exibição
    ordem = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento N:N com produtos
    produtos = relationship(
        "ProdutoModel",
        secondary="catalogo.produto_complemento_link",
        back_populates="complementos",
        viewonly=True,  # Leitura apenas, pois a relação real é no link
    )
    
    # Relacionamento N:N com itens de complemento (via tabela de associação)
    # Um complemento pode ter vários itens e um item pode pertencer a vários complementos
    itens = relationship(
        "AdicionalModel",
        secondary="catalogo.complemento_item_link",
        back_populates="complementos",
        viewonly=True,
    )
    
    # Mantido para compatibilidade (alias para itens)
    adicionais = relationship(
        "AdicionalModel",
        secondary="catalogo.complemento_item_link",
        back_populates="complementos",
        viewonly=True,
    )
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<Complemento(id={self.id}, nome='{self.nome}', empresa={self.empresa_id})>"


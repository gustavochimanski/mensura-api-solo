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
    
    # Ordem de exibição (padrão, pode ser sobrescrita na vinculação)
    ordem = Column(Integer, nullable=False, default=0)
    
    # NOTA: obrigatorio, quantitativo, minimo_itens e maximo_itens foram movidos
    # para as tabelas de vinculação (produto_complemento_link, receita_complemento_link, combo_complemento_link)
    
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
    
    # Relacionamento N:N com receitas
    receitas = relationship(
        "ReceitaModel",
        secondary="catalogo.receita_complemento_link",
        back_populates="complementos",
        viewonly=True,  # Leitura apenas, pois a relação real é no link
    )
    
    # Relacionamento N:N com combos
    combos = relationship(
        "ComboModel",
        secondary="catalogo.combo_complemento_link",
        back_populates="complementos",
        viewonly=True,  # Leitura apenas, pois a relação real é no link
    )
    
    # Vínculos de itens (produto/receita/combo) dentro do complemento.
    # Exposto como `adicionais` para o front (via service/adapter), mas no banco não existe mais
    # a entidade `catalogo.adicionais`.
    vinculos_itens = relationship(
        "ComplementoVinculoItemModel",
        back_populates="complemento",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<Complemento(id={self.id}, nome='{self.nome}', empresa={self.empresa_id})>"


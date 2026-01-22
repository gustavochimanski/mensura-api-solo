
from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class AdicionalModel(Base):
    """Modelo para adicionais (itens que podem ser usados em complementos, receitas, combos, etc.)"""
    __tablename__ = "adicionais"
    __table_args__ = {"schema": "catalogo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Vinculado a uma empresa
    empresa_id = Column(Integer, nullable=False, index=True)  # Sem FK para evitar dependência circular
    
    # Informações do item
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    # URL pública da imagem (ex.: MinIO)
    imagem = Column(String(255), nullable=True)
    preco = Column(Numeric(18, 2), nullable=False, default=0)
    custo = Column(Numeric(18, 2), nullable=False, default=0)  # Custo interno do item
    
    # Configurações
    ativo = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # DEPRECADO: Relacionamento N:N com complementos foi removido
    # complemento_item_link não existe mais - adicionais agora são vínculos de produtos/receitas/combos em complementos
    # complementos = relationship(
    #     "ComplementoModel",
    #     secondary="catalogo.complemento_item_link",
    #     back_populates="itens",
    #     viewonly=True,
    # )
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<Adicional(id={self.id}, nome='{self.nome}', empresa={self.empresa_id})>"


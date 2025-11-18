from pydantic import ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.db_connection import Base


class IngredienteModel(Base):
    """Modelo para ingredientes de receitas"""
    __tablename__ = "ingredientes"
    __table_args__ = (
        {"schema": "catalogo"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Vinculado a uma empresa
    empresa_id = Column(Integer, nullable=False, index=True)  # Sem FK para evitar dependência circular
    
    # Informações do ingrediente
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    unidade_medida = Column(String(10), nullable=True)  # ex: "KG", "L", "UN", "GR"
    
    # Configurações
    ativo = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento 1:1 com receita (um ingrediente só pode estar em uma receita)
    receita_ingrediente = relationship(
        "ReceitaIngredienteModel",
        back_populates="ingrediente",
        uselist=False,  # 1:1 relationship
    )
    
    model_config = ConfigDict(from_attributes=True)

    def __repr__(self):
        return f"<Ingrediente(id={self.id}, nome='{self.nome}', empresa={self.empresa_id})>"



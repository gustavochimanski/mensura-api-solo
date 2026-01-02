from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from sqlalchemy import DateTime
from pydantic import ConfigDict

class CaixaModel(Base):
    """Modelo para cadastro de caixas (CRUD simples)"""
    __tablename__ = "caixas"
    __table_args__ = (
        Index("idx_caixa_empresa", "empresa_id"),
        Index("idx_caixa_ativo", "ativo"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", back_populates="caixas")
    
    # Dados do caixa
    nome = Column(String(100), nullable=False)  # Nome/identificação do caixa
    descricao = Column(String(500), nullable=True)  # Descrição opcional
    ativo = Column(Boolean, default=True, nullable=False)  # Se o caixa está ativo
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamento com aberturas
    aberturas = relationship(
        "CaixaAberturaModel",
        back_populates="caixa",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)


from sqlalchemy import Column, Integer, Numeric, DateTime, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from pydantic import ConfigDict

class CaixaConferenciaModel(Base):
    """Armazena a conferência por tipo de meio de pagamento no fechamento do caixa"""
    __tablename__ = "caixa_conferencias"
    __table_args__ = (
        Index("idx_caixa_conferencia_caixa", "caixa_id"),
        Index("idx_caixa_conferencia_meio", "meio_pagamento_id"),
        {"schema": "financeiro"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    caixa_id = Column(Integer, ForeignKey("cadastros.caixas.id", ondelete="CASCADE"), nullable=False)
    caixa = relationship("CaixaModel", back_populates="conferencias")
    
    meio_pagamento_id = Column(Integer, ForeignKey("cadastros.meios_pagamento.id", ondelete="RESTRICT"), nullable=False)
    meio_pagamento = relationship("MeioPagamentoModel")
    
    # Valores esperados e conferidos
    valor_esperado = Column(Numeric(18, 2), nullable=False, default=0)  # Valor esperado baseado em transações
    valor_conferido = Column(Numeric(18, 2), nullable=False, default=0)  # Valor conferido no fechamento
    diferenca = Column(Numeric(18, 2), nullable=False, default=0)  # Diferença entre esperado e conferido
    
    # Quantidade de transações
    quantidade_transacoes = Column(Integer, nullable=False, default=0)
    
    # Observações específicas deste meio de pagamento
    observacoes = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    model_config = ConfigDict(from_attributes=True)


from sqlalchemy import Column, Integer, Numeric, DateTime, String, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

RetiradaTipo = SAEnum("SANGRIA", "DESPESA", name="retirada_tipo_enum", create_type=False, schema="cadastros")

class RetiradaModel(Base):
    __tablename__ = "caixas_retiradas"
    __table_args__ = (
        Index("idx_caixa_retirada_caixa_abertura", "caixa_abertura_id"),
        Index("idx_caixa_retirada_tipo", "tipo"),
        Index("idx_caixa_retirada_empresa", "empresa_id"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel")
    
    caixa_abertura_id = Column(Integer, ForeignKey("cadastros.caixa_aberturas.id", ondelete="CASCADE"), nullable=False)
    caixa_abertura = relationship("CaixaAberturaModel", back_populates="retiradas")
    
    usuario_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="RESTRICT"), nullable=False)
    usuario = relationship("UserModel", foreign_keys=[usuario_id])
    
    # Dados da retirada
    tipo = Column(RetiradaTipo, nullable=False)  # SANGRIA ou DESPESA
    valor = Column(Numeric(18, 2), nullable=False)  # Valor retirado
    observacoes = Column(String(500), nullable=True)  # Observações (obrigatório para DESPESA)
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)


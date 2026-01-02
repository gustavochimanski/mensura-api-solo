from sqlalchemy import Column, Integer, Numeric, DateTime, String, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

RetiradaTipo = SAEnum("SANGRIA", "DESPESA", name="retirada_tipo_enum", create_type=False, schema="cadastros")

class RetiradaModel(Base):
    __tablename__ = "retiradas_caixa"
    __table_args__ = (
        Index("idx_retirada_caixa", "caixa_id"),
        Index("idx_retirada_tipo", "tipo"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    caixa_id = Column(Integer, ForeignKey("cadastros.caixas.id", ondelete="CASCADE"), nullable=False)
    caixa = relationship("CaixaModel", back_populates="retiradas")
    
    usuario_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="RESTRICT"), nullable=False)
    usuario = relationship("UserModel", foreign_keys=[usuario_id])
    
    # Dados da retirada
    tipo = Column(RetiradaTipo, nullable=False)  # SANGRIA ou DESPESA
    valor = Column(Numeric(18, 2), nullable=False)  # Valor retirado
    observacoes = Column(String(500), nullable=True)  # Observações (obrigatório para DESPESA)
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)


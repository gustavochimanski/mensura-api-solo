from sqlalchemy import Column, String, Boolean, Enum as SAEnum, Integer
import uuid
from app.database.db_connection import Base

# Enum para tipos genéricos (para agrupar métodos semelhantes)
MeioPagamentoTipo = SAEnum(
    "CARTAO_ENTREGA", "PIX_ENTREGA", "DINHEIRO", "CARTAO_ONLINE", "PIX_ONLINE",
    name="meio_pagamento_tipo_enum",
    create_type=False
)

class MeioPagamentoModel(Base):
    __tablename__ = "meios_pagamento_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)  # Nome amigável
    tipo = Column(MeioPagamentoTipo, nullable=False)        # Categoria
    ativo = Column(Boolean, default=True, nullable=False)
    from sqlalchemy import DateTime, func

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)



from sqlalchemy import Column, String, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False, unique=True)  # Nome amigável
    tipo = Column(MeioPagamentoTipo, nullable=False)        # Categoria
    ativo = Column(Boolean, default=True, nullable=False)

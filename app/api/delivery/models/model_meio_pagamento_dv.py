from sqlalchemy import Column, String, Boolean, Enum as SAEnum, Integer
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed

# Enum para tipos genéricos (para agrupar métodos semelhantes)
MeioPagamentoTipo = SAEnum(
    "CARTAO_ENTREGA", "PIX_ENTREGA", "DINHEIRO", "CARTAO_ONLINE", "PIX_ONLINE",
    name="meio_pagamento_tipo_enum",
    create_type=True
)

class MeioPagamentoModel(Base):
    __tablename__ = "meios_pagamento_dv"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)  # Nome amigável
    tipo = Column(MeioPagamentoTipo, nullable=False)        # Categoria
    ativo = Column(Boolean, default=True, nullable=False)
    from sqlalchemy import DateTime

    created_at = Column(DateTime, default=now_trimmed)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed)
    def display(self):
        return f"{self.nome}"



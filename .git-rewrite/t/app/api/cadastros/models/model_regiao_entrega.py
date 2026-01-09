from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class RegiaoEntregaModel(Base):
    __tablename__ = "regioes_entrega"
    __table_args__ = {"schema": "cadastros"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id"), nullable=False)

    descricao = Column(String(120), nullable=True)
    distancia_min_km = Column(Numeric(10, 2), nullable=False, default=0)
    distancia_max_km = Column(Numeric(10, 2), nullable=True)

    taxa_entrega = Column(Numeric(10, 2), nullable=False, default=0)
    tempo_estimado_min = Column(Integer, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)


    empresa = relationship("EmpresaModel", back_populates="regioes_entrega")

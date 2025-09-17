from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class RegiaoEntregaModel(Base):
    __tablename__ = "regioes_entrega"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("mensura.empresas.id"), nullable=False)

    cep = Column(String(9), nullable=True)  # 8 dígitos ou com hífen
    bairro = Column(String(120), nullable=False)
    cidade = Column(String(120), nullable=False)
    uf = Column(String(2), nullable=False)

    latitude = Column(Numeric(10, 6), nullable=True)
    longitude = Column(Numeric(10, 6), nullable=True)
    raio_km = Column(Numeric(5, 2), nullable=True, default=2.0)  # Raio de cobertura em km

    taxa_entrega = Column(Numeric(10, 2), nullable=False, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)


    empresa = relationship("EmpresaModel", back_populates="regioes_entrega")
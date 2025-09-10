from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class RegiaoEntregaModel(Base):
    __tablename__ = "regioes_entrega"
    __table_args__ = {"schema": "delivery"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("mensura.empresas.id"), nullable=False)

    # Campos básicos de endereço
    cep = Column(String(9), nullable=True)  # 8 dígitos ou com hífen
    logradouro = Column(String(255), nullable=True)
    complemento = Column(String(255), nullable=True)
    unidade = Column(String(50), nullable=True)
    bairro = Column(String(120), nullable=False)
    cidade = Column(String(120), nullable=False)
    uf = Column(String(2), nullable=False)
    estado = Column(String(120), nullable=True)
    regiao = Column(String(50), nullable=True)

    # Dados do IBGE
    ibge = Column(String(10), nullable=True)
    gia = Column(String(10), nullable=True)
    ddd = Column(String(5), nullable=True)
    siafi = Column(String(10), nullable=True)

    # Geolocalização
    latitude = Column(Numeric(10, 6), nullable=True)
    longitude = Column(Numeric(10, 6), nullable=True)

    # Configurações de entrega
    taxa_entrega = Column(Numeric(10, 2), nullable=False, default=0)
    ativo = Column(Boolean, default=True, nullable=False)

    # Auditoria
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    # Relacionamentos
    empresa = relationship("EmpresaModel", back_populates="regioes_entrega")

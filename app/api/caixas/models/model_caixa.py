from sqlalchemy import Column, Integer, Numeric, DateTime, String, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from pydantic import ConfigDict

CaixaStatus = SAEnum("ABERTO", "FECHADO", name="caixa_status_enum", create_type=False, schema="cadastros")

class CaixaModel(Base):
    __tablename__ = "caixas"
    __table_args__ = (
        Index("idx_caixa_empresa", "empresa_id"),
        Index("idx_caixa_status", "status"),
        Index("idx_caixa_data_abertura", "data_abertura"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", back_populates="caixas")
    
    usuario_id_abertura = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="RESTRICT"), nullable=False)
    usuario_abertura = relationship("UserModel", foreign_keys=[usuario_id_abertura])
    
    usuario_id_fechamento = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario_fechamento = relationship("UserModel", foreign_keys=[usuario_id_fechamento])
    
    # Valores
    valor_inicial = Column(Numeric(18, 2), nullable=False, default=0)  # Valor em dinheiro no caixa
    valor_final = Column(Numeric(18, 2), nullable=True)  # Valor informado no fechamento
    saldo_esperado = Column(Numeric(18, 2), nullable=True)  # Calculado: inicial + entradas - saídas
    saldo_real = Column(Numeric(18, 2), nullable=True)  # Valor real contado no fechamento
    diferenca = Column(Numeric(18, 2), nullable=True)  # Diferença entre esperado e real
    
    # Status e datas
    status = Column(CaixaStatus, nullable=False, default="ABERTO")
    data_abertura = Column(DateTime, default=now_trimmed, nullable=False)  # Data/hora automática (timestamp)
    data_fechamento = Column(DateTime, nullable=True)  # Data/hora automática (timestamp)
    data_hora_abertura = Column(DateTime, nullable=True)  # Data/hora informada pelo usuário na abertura
    data_hora_fechamento = Column(DateTime, nullable=True)  # Data/hora informada pelo usuário no fechamento
    
    # Observações
    observacoes_abertura = Column(String(500), nullable=True)
    observacoes_fechamento = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamento com conferências
    conferencias = relationship(
        "CaixaConferenciaModel",
        back_populates="caixa",
        cascade="all, delete-orphan"
    )
    
    # Relacionamento com retiradas
    retiradas = relationship(
        "RetiradaModel",
        back_populates="caixa",
        cascade="all, delete-orphan"
    )

    model_config = ConfigDict(from_attributes=True)


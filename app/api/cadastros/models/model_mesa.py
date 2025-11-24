# app/api/mesas/models/model_mesa.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.types import TypeDecorator, String as SATypeString
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class StatusMesa(str, enum.Enum):
#
    """Status possíveis para uma mesa"""
    DISPONIVEL = "D"  # Disponível
    OCUPADA = "O"     # Ocupada
    RESERVADA = "R"   # Reservada

    @classmethod
    def _missing_(cls, value):
        if value is None:
            return None
        normalized = str(value).upper().strip()
        alias_map = {
            "D": cls.DISPONIVEL,
            "O": cls.OCUPADA,
            "R": cls.RESERVADA,
            "DISPONIVEL": cls.DISPONIVEL,
            "OCUPADA": cls.OCUPADA,
            "RESERVADA": cls.RESERVADA,
            "LIVRE": cls.DISPONIVEL,
            "DISPONÍVEL": cls.DISPONIVEL,
        }
        return alias_map.get(normalized, None)


class StatusMesaType(TypeDecorator):
    """TypeDecorator para mapear valores legados de status."""

    impl = SATypeString(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if isinstance(value, StatusMesa):
            # Grava a letra do enum no banco
            return value.value

        alias = StatusMesa._missing_(value)
        if alias is None:
            raise ValueError(f"Status de mesa inválido: {value}")
        # Grava a letra do enum no banco (D/O/R)
        return alias.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        alias = StatusMesa._missing_(value)
        if alias is None:
            raise LookupError(
                f"Valor de status de mesa desconhecido no banco: {value}"
            )
        return alias


class MesaModel(Base):
    __tablename__ = "mesas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_mesa_empresa_codigo"),
        UniqueConstraint("empresa_id", "numero", name="uq_mesa_empresa_numero"),
        Index("idx_mesa_empresa", "empresa_id"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True)
    codigo = Column(Numeric(10, 2), nullable=False)  # Número real obrigatório
    numero = Column(String(10), nullable=False)
    descricao = Column(String(100), nullable=True)
    capacidade = Column(Integer, nullable=False, default=4)
    status = Column(StatusMesaType(), nullable=False, default=StatusMesa.DISPONIVEL)
    ativa = Column(String(1), nullable=False, default="S")  # S/N para ativa/inativa
    
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), nullable=False)
    empresa = relationship("EmpresaModel", lazy="select")

    # Relacionamentos
    # Migrado para modelos unificados - pedidos agora usam PedidoUnificadoModel
    # pedidos = relationship("PedidoMesaModel", back_populates="mesa", cascade="all, delete-orphan")
    cliente_atual_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente_atual = relationship("ClienteModel", lazy="select")
    # historico = relationship("MesaHistoricoModel", back_populates="mesa", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    @hybrid_property
    def status_descricao(self) -> str:
        """Retorna a descrição do status"""
        status_map = {
            StatusMesa.DISPONIVEL: "Disponível",
            StatusMesa.OCUPADA: "Ocupada", 
            StatusMesa.RESERVADA: "Reservada"
        }
        status = self.status
        if not isinstance(status, StatusMesa):
            try:
                status = StatusMesa(status)
            except ValueError:
                status = None
        return status_map.get(status, "Desconhecido")

    @hybrid_property
    def status_cor(self) -> str:
        """Retorna a cor do status para interface"""
        cor_map = {
            StatusMesa.DISPONIVEL: "green",
            StatusMesa.OCUPADA: "red",
            StatusMesa.RESERVADA: "orange"
        }
        return cor_map.get(self.status, "gray")

    @property
    def label(self) -> str:
        """Label para exibição"""
        return f"Mesa {self.numero}"

    @property
    def is_ocupada(self) -> bool:
        """Verifica se a mesa está ocupada"""
        return self.status == StatusMesa.OCUPADA

    @property
    def is_disponivel(self) -> bool:
        """Verifica se a mesa está disponível"""
        return self.status == StatusMesa.DISPONIVEL

    @property
    def is_reservada(self) -> bool:
        """Verifica se a mesa está reservada"""
        return self.status == StatusMesa.RESERVADA


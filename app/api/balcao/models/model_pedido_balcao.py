# app/api/balcao/models/model_pedido_balcao.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum as SAEnum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class StatusPedidoBalcao(enum.Enum):
    """Status possíveis para um pedido de balcão.

    Alinhado ao fluxo de delivery (PedidoStatusEnum), sem o status 'S' (saiu para entrega).
    """

    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


# PENDENTE: P
# IMPRESSAO: I
# PREPARANDO: R
# ENTREGUE: E
# CANCELADO: C
# EDITADO: D
# EM_EDICAO: X
# AGUARDANDO_PAGAMENTO: A

# ENUM do PostgreSQL com schema correto
StatusPedidoBalcaoEnum = SAEnum(
    "P", "I", "R", "E", "C", "D", "X", "A",
    name="statuspedidobalcao",
    create_type=False,
    schema="balcao"
)


class PedidoBalcaoModel(Base):
    __tablename__ = "pedidos_balcao"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_pedido", name="uq_pedidos_balcao_empresa_numero"),
        Index("idx_pedidos_balcao_empresa", "empresa_id"),
        {"schema": "balcao"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", lazy="select")
    
    # Relacionamentos
    mesa_id = Column(Integer, ForeignKey("cadastros.mesas.id", ondelete="SET NULL"), nullable=True)
    mesa = relationship("MesaModel", lazy="select")
    
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    # Dados do pedido
    numero_pedido = Column(String(20), nullable=False, unique=True)
    status = Column(StatusPedidoBalcaoEnum, nullable=False, default="P")
    observacoes = Column(String(500), nullable=True)
    
    # Valores
    valor_total = Column(Numeric(18, 2), nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamento com itens do pedido
    itens = relationship("PedidoBalcaoItemModel", back_populates="pedido", cascade="all, delete-orphan")
    
    # Relacionamento com histórico
    historico = relationship("PedidoBalcaoHistoricoModel", back_populates="pedido", cascade="all, delete-orphan")

    @property
    def status_descricao(self) -> str:
        """Retorna a descrição do status"""
        status_key = (
            self.status.value
            if isinstance(self.status, StatusPedidoBalcao)
            else str(self.status)
        )
        status_map = {
            StatusPedidoBalcao.PENDENTE.value: "Pendente",
            StatusPedidoBalcao.IMPRESSAO.value: "Em impressão",
            StatusPedidoBalcao.PREPARANDO.value: "Preparando",
            StatusPedidoBalcao.ENTREGUE.value: "Entregue",
            StatusPedidoBalcao.CANCELADO.value: "Cancelado",
            StatusPedidoBalcao.EDITADO.value: "Editado",
            StatusPedidoBalcao.EM_EDICAO.value: "Em edição",
            StatusPedidoBalcao.AGUARDANDO_PAGAMENTO.value: "Aguardando pagamento",
        }
        return status_map.get(status_key, "Desconhecido")

    @property
    def status_cor(self) -> str:
        """Retorna a cor do status para interface"""
        status_key = (
            self.status.value
            if isinstance(self.status, StatusPedidoBalcao)
            else str(self.status)
        )
        cor_map = {
            StatusPedidoBalcao.PENDENTE.value: "orange",
            StatusPedidoBalcao.IMPRESSAO.value: "blue",
            StatusPedidoBalcao.PREPARANDO.value: "yellow",
            StatusPedidoBalcao.ENTREGUE.value: "green",
            StatusPedidoBalcao.CANCELADO.value: "red",
            StatusPedidoBalcao.EDITADO.value: "purple",
            StatusPedidoBalcao.EM_EDICAO.value: "teal",
            StatusPedidoBalcao.AGUARDANDO_PAGAMENTO.value: "cyan",
        }
        return cor_map.get(status_key, "gray")


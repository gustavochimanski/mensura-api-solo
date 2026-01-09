# app/api/mesas/models/model_pedido_mesa.py
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    Enum as SAEnum,
    func,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class StatusPedidoMesa(enum.Enum):
    """Status possíveis para um pedido de mesa.

    Alinhado com os status de delivery (PedidoStatusEnum), exceto pelo status 'S'
    (Saiu para entrega), que não se aplica aos pedidos de mesa.
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
StatusPedidoMesaEnum = SAEnum(
    "P", "I", "R", "E", "C", "D", "X", "A",
    name="statuspedidomesa",
    create_type=False,
    schema="mesas"
)


class PedidoMesaModel(Base):
    __tablename__ = "pedidos_mesa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero_pedido", name="uq_pedidos_mesa_empresa_numero"),
        Index("idx_pedidos_mesa_empresa", "empresa_id"),
        {"schema": "mesas"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False)
    empresa = relationship("EmpresaModel", lazy="select")
    
    # Relacionamentos
    mesa_id = Column(Integer, ForeignKey("cadastros.mesas.id", ondelete="CASCADE"), nullable=False)
    mesa = relationship("MesaModel", back_populates="pedidos")
    
    cliente_id = Column(Integer, ForeignKey("cadastros.clientes.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteModel", lazy="select")
    
    meio_pagamento_id = Column(Integer, ForeignKey("cadastros.meios_pagamento.id", ondelete="SET NULL"), nullable=True)
    meio_pagamento = relationship("MeioPagamentoModel", lazy="select")
    
    # Dados do pedido
    numero_pedido = Column(String(20), nullable=False, unique=True)
    status = Column(StatusPedidoMesaEnum, nullable=False, default="P")
    observacoes = Column(String(500), nullable=True)
    num_pessoas = Column(Integer, nullable=True)
    produtos_snapshot = Column(JSON, nullable=True)
    
    # Valores
    valor_total = Column(Numeric(18, 2), nullable=False, default=0)
    troco_para = Column(Numeric(18, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=now_trimmed, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamento com itens do pedido
    itens = relationship("PedidoMesaItemModel", back_populates="pedido", cascade="all, delete-orphan")

    @property
    def status_descricao(self) -> str:
        """Retorna a descrição do status"""
        status_map = {
            StatusPedidoMesa.PENDENTE: "Pendente",
            StatusPedidoMesa.IMPRESSAO: "Em impressão",
            StatusPedidoMesa.PREPARANDO: "Preparando",
            StatusPedidoMesa.ENTREGUE: "Entregue",
            StatusPedidoMesa.CANCELADO: "Cancelado",
            StatusPedidoMesa.EDITADO: "Editado",
            StatusPedidoMesa.EM_EDICAO: "Em edição",
            StatusPedidoMesa.AGUARDANDO_PAGAMENTO: "Aguardando pagamento",
        }
        return status_map.get(self.status, "Desconhecido")

    @property
    def status_cor(self) -> str:
        """Retorna a cor do status para interface"""
        cor_map = {
            StatusPedidoMesa.PENDENTE: "orange",
            StatusPedidoMesa.IMPRESSAO: "blue",
            StatusPedidoMesa.PREPARANDO: "yellow",
            StatusPedidoMesa.ENTREGUE: "green",
            StatusPedidoMesa.CANCELADO: "red",
            StatusPedidoMesa.EDITADO: "purple",
            StatusPedidoMesa.EM_EDICAO: "teal",
            StatusPedidoMesa.AGUARDANDO_PAGAMENTO: "cyan",
        }
        return cor_map.get(self.status, "gray")

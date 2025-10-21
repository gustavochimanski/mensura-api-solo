# app/api/mesas/models/model_pedido_mesa.py
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum, func
from sqlalchemy.orm import relationship
import enum

from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed


class StatusPedidoMesa(enum.Enum):
    """Status possíveis para um pedido de mesa"""
    PENDENTE = "P"      # Pendente
    CONFIRMADO = "C"    # Confirmado
    PREPARANDO = "R"    # Preparando
    PRONTO = "T"        # Pronto
    ENTREGUE = "E"      # Entregue
    CANCELADO = "X"     # Cancelado


class PedidoMesaModel(Base):
    __tablename__ = "pedidos_mesa"
    __table_args__ = {"schema": "mesas"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    mesa_id = Column(Integer, ForeignKey("mesas.mesa.id", ondelete="CASCADE"), nullable=False)
    mesa = relationship("MesaModel", back_populates="pedidos")
    
    cliente_id = Column(Integer, ForeignKey("delivery.clientes_dv.id", ondelete="SET NULL"), nullable=True)
    cliente = relationship("ClienteDeliveryModel")
    
    # Dados do pedido
    numero_pedido = Column(String(20), nullable=False, unique=True)
    status = Column(Enum(StatusPedidoMesa), nullable=False, default=StatusPedidoMesa.PENDENTE)
    observacoes = Column(String(500), nullable=True)
    
    # Valores
    valor_total = Column(Numeric(18, 2), nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)
    
    # Relacionamento com itens do pedido
    itens = relationship("PedidoMesaItemModel", back_populates="pedido", cascade="all, delete-orphan")

    @property
    def status_descricao(self) -> str:
        """Retorna a descrição do status"""
        status_map = {
            StatusPedidoMesa.PENDENTE: "Pendente",
            StatusPedidoMesa.CONFIRMADO: "Confirmado",
            StatusPedidoMesa.PREPARANDO: "Preparando",
            StatusPedidoMesa.PRONTO: "Pronto",
            StatusPedidoMesa.ENTREGUE: "Entregue",
            StatusPedidoMesa.CANCELADO: "Cancelado"
        }
        return status_map.get(self.status, "Desconhecido")

    @property
    def status_cor(self) -> str:
        """Retorna a cor do status para interface"""
        cor_map = {
            StatusPedidoMesa.PENDENTE: "orange",
            StatusPedidoMesa.CONFIRMADO: "blue",
            StatusPedidoMesa.PREPARANDO: "yellow",
            StatusPedidoMesa.PRONTO: "green",
            StatusPedidoMesa.ENTREGUE: "gray",
            StatusPedidoMesa.CANCELADO: "red"
        }
        return cor_map.get(self.status, "gray")

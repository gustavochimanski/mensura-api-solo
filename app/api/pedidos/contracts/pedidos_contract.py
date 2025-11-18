"""
Contract (Interface) para acesso a pedidos do bounded context de Pedidos.
Permite que outros bounded contexts acessem pedidos sem acoplamento direto.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel


class TipoPedidoDTO(str, Enum):
    """Tipo de pedido."""
    MESA = "MESA"
    BALCAO = "BALCAO"
    DELIVERY = "DELIVERY"


class StatusPedidoDTO(str, Enum):
    """Status de pedido."""
    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    SAIU_PARA_ENTREGA = "S"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


class ClienteMinDTO(BaseModel):
    """DTO mínimo de cliente."""
    id: Optional[int] = None
    nome: Optional[str] = None


class PedidoMinDTO(BaseModel):
    """DTO mínimo de pedido para comunicação entre contextos."""
    id: int
    empresa_id: int
    numero_pedido: str
    tipo_pedido: TipoPedidoDTO
    status: StatusPedidoDTO
    valor_total: Decimal | float
    cliente: Optional[ClienteMinDTO] = None
    mesa_id: Optional[int] = None
    endereco_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    observacoes: Optional[str] = None


class IPedidosContract(ABC):
    """Contrato para acesso a pedidos do bounded context de Pedidos."""

    @abstractmethod
    def obter_pedido_por_id(self, pedido_id: int) -> Optional[PedidoMinDTO]:
        """Obtém um pedido por ID."""
        raise NotImplementedError

    @abstractmethod
    def listar_abertos(
        self,
        *,
        empresa_id: int,
        tipo_pedido: Optional[TipoPedidoDTO] = None
    ) -> List[PedidoMinDTO]:
        """Lista pedidos abertos (não finalizados)."""
        raise NotImplementedError

    @abstractmethod
    def listar_finalizados(
        self,
        *,
        empresa_id: int,
        data_filtro: Optional[date] = None,
        tipo_pedido: Optional[TipoPedidoDTO] = None
    ) -> List[PedidoMinDTO]:
        """Lista pedidos finalizados (status ENTREGUE)."""
        raise NotImplementedError

    @abstractmethod
    def listar_por_cliente(
        self,
        cliente_id: int,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[TipoPedidoDTO] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[PedidoMinDTO]:
        """Lista pedidos de um cliente específico."""
        raise NotImplementedError

    @abstractmethod
    def listar_abertos_por_mesa(
        self,
        mesa_id: int,
        *,
        empresa_id: Optional[int] = None
    ) -> List[PedidoMinDTO]:
        """Lista pedidos abertos associados a uma mesa."""
        raise NotImplementedError

    @abstractmethod
    def contar_pedidos_abertos(
        self,
        *,
        empresa_id: int,
        tipo_pedido: Optional[TipoPedidoDTO] = None
    ) -> int:
        """Conta quantos pedidos estão abertos."""
        raise NotImplementedError


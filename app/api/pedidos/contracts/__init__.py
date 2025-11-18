"""
Contracts do bounded context de Pedidos.
"""

from .pedidos_contract import (
    IPedidosContract,
    PedidoMinDTO,
    ClienteMinDTO,
    TipoPedidoDTO,
    StatusPedidoDTO,
)
from .dependencies import get_pedidos_contract

__all__ = [
    "IPedidosContract",
    "PedidoMinDTO",
    "ClienteMinDTO",
    "TipoPedidoDTO",
    "StatusPedidoDTO",
    "get_pedidos_contract",
]


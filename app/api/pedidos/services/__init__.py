"""
Services do bounded context de Pedidos.
"""

from .service_pedido import PedidoService
# Mantidos para compatibilidade durante migração
from .service_pedidos_balcao import PedidoBalcaoService
from .service_pedidos_mesa import PedidoMesaService

__all__ = [
    "PedidoService",
    "PedidoBalcaoService",  # Mantido para compatibilidade
    "PedidoMesaService",  # Mantido para compatibilidade
]


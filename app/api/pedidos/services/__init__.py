"""
Services do bounded context de Pedidos.
"""

from .service_pedido import PedidoService
from .service_pedido_admin import PedidoAdminService
# Mantidos para compatibilidade durante migração
from .service_pedidos_balcao import PedidoBalcaoService
from .service_pedidos_mesa import PedidoMesaService

__all__ = [
    "PedidoService",
    "PedidoAdminService",
    "PedidoBalcaoService",  # Mantido para compatibilidade
    "PedidoMesaService",  # Mantido para compatibilidade
]


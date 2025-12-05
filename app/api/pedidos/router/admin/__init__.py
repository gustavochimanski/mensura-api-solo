"""
Routers admin do bounded context de Pedidos.
"""

from .router_pedidos_admin import router as router_pedidos_admin
from .router_pedidos_admin_v2 import router as router_pedidos_admin_v2

__all__ = ["router_pedidos_admin", "router_pedidos_admin_v2"]


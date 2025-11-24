"""
Router principal do bounded context de Pedidos.
"""
from fastapi import APIRouter

from app.api.pedidos.router.admin.router_pedidos_admin import router as router_pedidos_admin
from app.api.pedidos.router.admin.router_pedidos_mesa_admin import router as router_pedidos_mesa_admin
from app.api.pedidos.router.admin.router_pedidos_delivery_admin import router as router_pedidos_delivery_admin
from app.api.pedidos.router.client.router_pedidos_client import router as router_pedidos_client

api_pedidos = APIRouter(
    tags=["API - Pedidos Unificados"]
)

# Routers admin
api_pedidos.include_router(router_pedidos_admin)
api_pedidos.include_router(router_pedidos_mesa_admin)
api_pedidos.include_router(router_pedidos_delivery_admin)

# Routers client
api_pedidos.include_router(router_pedidos_client)


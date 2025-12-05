"""
Router principal do bounded context de Pedidos.
Todos os endpoints de pedidos (Delivery, Mesa, Balcão) estão unificados em router_pedidos_admin.
"""
from fastapi import APIRouter

from app.api.pedidos.router.admin.router_pedidos_admin import router as router_pedidos_admin
from app.api.pedidos.router.admin.router_pedidos_admin_v2 import router as router_pedidos_admin_v2
from app.api.pedidos.router.client.router_pedidos_client import router as router_pedidos_client

api_pedidos = APIRouter(
    tags=["API - Pedidos Unificados"]
)

# Router admin (v1 legado)
api_pedidos.include_router(router_pedidos_admin)

# Router admin v2 (unificado para novos contratos)
api_pedidos.include_router(router_pedidos_admin_v2)

# Routers client
api_pedidos.include_router(router_pedidos_client)


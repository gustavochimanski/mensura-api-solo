"""
Router principal do bounded context de Pedidos.
"""
from fastapi import APIRouter

from app.api.pedidos.router.admin.router_pedidos_admin import router as router_pedidos_admin

api_pedidos = APIRouter(
    tags=["API - Pedidos Unificados"]
)

# Routers admin
api_pedidos.include_router(router_pedidos_admin)

# Routers client (a serem criados quando necessário)
# api_pedidos.include_router(router_pedidos_client)


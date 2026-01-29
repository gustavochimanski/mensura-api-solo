"""
Router principal do bounded context de Pedidos.
Todos os endpoints de pedidos (Delivery, Mesa, Balcão) estão unificados em router_pedidos_admin.
"""
from fastapi import APIRouter
from fastapi import Depends

from app.api.pedidos.router.admin.router_pedidos_admin import router as router_pedidos_admin
from app.api.pedidos.router.client.router_pedidos_client import router as router_pedidos_client
from app.core.authorization import require_domain

api_pedidos = APIRouter()

# Router admin unificado
api_pedidos.include_router(router_pedidos_admin, dependencies=[Depends(require_domain("pedidos"))])

# Routers client
api_pedidos.include_router(router_pedidos_client)


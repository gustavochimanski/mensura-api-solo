from fastapi import APIRouter

from app.api.balcao.router.admin.router_pedidos_balcao_admin import router as router_pedidos_balcao_admin
from app.api.balcao.router.client.router_pedidos_balcao_client import router as router_pedidos_balcao_client

api_balcao = APIRouter(
    tags=["API - Balcão"]
)

# Routers para admin
api_balcao.include_router(router_pedidos_balcao_admin)

# Routers para client
api_balcao.include_router(router_pedidos_balcao_client)


from fastapi import APIRouter

from app.api.mesas.router.admin.router_mesas_admin import router as router_mesas_admin
from app.api.mesas.router.admin.router_pedidos_mesa_admin import router as router_pedidos_mesa_admin

api_mesas = APIRouter(
    tags=["API - Mesas"]
)

# Routers para admin (usam get_current_user)
api_mesas.include_router(router_mesas_admin)
api_mesas.include_router(router_pedidos_mesa_admin)



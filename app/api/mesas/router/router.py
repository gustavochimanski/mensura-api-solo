from fastapi import APIRouter

from app.api.mesas.router.admin.router_mesas_admin import router as router_mesas_admin
from app.api.mesas.router.client.router_mesas_client import router as router_mesas_client

api_mesas = APIRouter()

# Routers para admin (usam get_current_user)
api_mesas.include_router(router_mesas_admin)

# Routers para clientes (usam get_current_client)
api_mesas.include_router(router_mesas_client)

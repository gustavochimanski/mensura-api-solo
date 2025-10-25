from fastapi import APIRouter

from app.api.mesas.router.admin.router_mesas_admin import router as router_mesas_admin

api_mesas = APIRouter()

# Routers para admin (usam get_current_user)
api_mesas.include_router(router_mesas_admin)



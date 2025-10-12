from fastapi import APIRouter, Depends

from app.api.delivery.router import router_printer

api_delivery = APIRouter()

# Routers públicos (sem autenticação)
api_delivery.include_router(router_printer.router)
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()

# Routers para clientes (usam super_token)
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()

# Routers para admin (usam get_current_user)
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()
api_delivery.include_router()

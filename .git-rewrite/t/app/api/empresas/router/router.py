# app/api/empresas/router/router.py

from fastapi import APIRouter

from app.api.empresas.router.admin import (
    router_empresa_admin,
)
from app.api.empresas.router.public import (
    router_empresa_public,
)

api_empresas = APIRouter(
    tags=["API - Empresas"]
)

# Routers públicos (sem autenticação)
api_empresas.include_router(router_empresa_public)

# Routers para admin (usam get_current_user)
api_empresas.include_router(router_empresa_admin)


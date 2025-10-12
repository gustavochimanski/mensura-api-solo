# app/api/mensura/router.py

from fastapi import APIRouter, Depends

from app.api.mensura.router.empresa.router_empresa_admin import (
    router as router_empresa_admin,
)
from app.api.mensura.router.empresa.router_empresa_public import (
    router as router_empresa_public,
)
from app.api.mensura.router.router_usuario import router as router_usuario
from app.api.mensura.router.geoapify.router_geoapify_client import (
    router as router_geoapify_client,
)
from app.api.mensura.router.geoapify.router_geoapify_admin import (
    router as router_geoapify_admin,
)
from app.api.mensura.router.router_endereco_admin import (
    router as router_endereco_admin,
)
from app.api.mensura.router.router_produtos import router as router_produtos
from app.core.admin_dependencies import get_current_user

mensura_router = APIRouter()
mensura_router.include_router(router_empresa_admin, dependencies=[Depends(get_current_user)])
mensura_router.include_router(router_empresa_public)
mensura_router.include_router(
    router_endereco_admin, dependencies=[Depends(get_current_user)]
)
mensura_router.include_router(router_geoapify_client)
mensura_router.include_router(router_geoapify_admin)
mensura_router.include_router(router_produtos, dependencies=[Depends(get_current_user)])
mensura_router.include_router(router_usuario, dependencies=[Depends(get_current_user)])

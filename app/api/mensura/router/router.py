# app/api/mensura/router.py

from fastapi import APIRouter, Depends

from app.api.mensura.router.router_empresa import router as router_empresa
from app.api.mensura.router.router_empresa_client import router as router_empresa_client
from app.api.mensura.router.router_usuario import router as router_usuario
from app.api.mensura.router.router_geo_api_fy import router as router_geoapify
from app.api.mensura.router.router_endereco import router as router_endereco
from app.api.mensura.router.router_produtos import router as router_produtos
from app.api.mensura.router.router_impressora import router as router_impressora
from app.core.admin_dependencies import get_current_user

router = APIRouter()
router.include_router(router_empresa, dependencies=[Depends(get_current_user)])
router.include_router(router_empresa_client)
router.include_router(router_endereco, dependencies=[Depends(get_current_user)])
router.include_router(router_geoapify)
router.include_router(router_produtos, dependencies=[Depends(get_current_user)])
router.include_router(router_usuario, dependencies=[Depends(get_current_user)])
router.include_router(router_impressora)

# app/api/mensura/router.py

from fastapi import APIRouter

from app.core.dependencies import get_current_user
from app.api.mensura.router.empresa_router import router as router_empresa
from app.api.mensura.router.usuario_router import router as router_usuario
from app.api.mensura.router.endereco_router import router as router_endereco

router = APIRouter()

router.include_router(router_empresa)
router.include_router(router_usuario)
router.include_router(router_endereco)

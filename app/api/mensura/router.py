# app/api/mensura/router.py

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.api.mensura.controllers.empresa_controller import router as router_empresa
from app.api.mensura.controllers.usuario_controller import router as router_usuario
from app.api.mensura.controllers.endereco_controller import router as router_endereco

router = APIRouter()

router.include_router(router_empresa, dependencies=[Depends(get_current_user)])
router.include_router(router_usuario, dependencies=[Depends(get_current_user)])
router.include_router(router_endereco, dependencies=[Depends(get_current_user)])

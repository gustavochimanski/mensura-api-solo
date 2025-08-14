# app/api/mensura/router.py

from fastapi import APIRouter

from app.api.mensura.router.router_empresa import router as router_empresa
from app.api.mensura.router.router_usuario import router as router_usuario
from app.api.mensura.router.router_endereco import router as router_endereco
from app.api.mensura.router.router_produtos import router as router_produtos
router = APIRouter()

router.include_router(router_empresa)
router.include_router(router_usuario)
router.include_router(router_endereco)
router.include_router(router_produtos)

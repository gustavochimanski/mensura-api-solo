from fastapi import APIRouter

from app.api.caixas.router.router_caixa_crud import router as router_caixa_crud
from app.api.caixas.router.router_caixa_abertura import router as router_caixa_abertura
from app.api.caixas.router.router_caixa_admin import router as router_caixa_admin

# Router principal que agrupa todos os routers de caixa
router = APIRouter(
    tags=["API - Caixa"]
)

# Inclui todos os sub-routers
router.include_router(router_caixa_crud)
router.include_router(router_caixa_abertura)
router.include_router(router_caixa_admin)


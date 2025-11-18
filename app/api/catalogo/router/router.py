from fastapi import APIRouter
from app.api.catalogo.router.admin import router_produtos, router_combos, router_adicionais, router_receitas

router = APIRouter()

router.include_router(router_produtos.router)
router.include_router(router_combos.router)
router.include_router(router_adicionais.router)
router.include_router(router_receitas.router)


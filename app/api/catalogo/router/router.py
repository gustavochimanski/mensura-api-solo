from fastapi import APIRouter
from app.api.catalogo.router.admin import (
    router_produtos,
    router_combos,
    router_adicionais,
    router_receitas,
)
from app.api.catalogo.router.client import router_adicionais_client

router = APIRouter()

# Rotas admin (usam autenticação de admin)
router.include_router(router_produtos.router)
router.include_router(router_combos.router)
router.include_router(router_adicionais.router)
router.include_router(router_receitas.router)

# Rotas client (usam X-Super-Token)
router.include_router(router_adicionais_client)

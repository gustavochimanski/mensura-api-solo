from fastapi import APIRouter
from app.api.catalogo.router.admin import (
    router_produtos,
    router_combos,
    router_complementos,
    router_adicionais,
    router_receitas,
    router_busca_global,
)
from app.api.catalogo.router.client import (
    router_complementos_client,
    router_busca_global_client,
)

router = APIRouter()

# Rotas admin (usam autenticação de admin)
router.include_router(router_produtos.router)
router.include_router(router_combos.router)
router.include_router(router_complementos.router)
router.include_router(router_adicionais.router)
router.include_router(router_receitas.router)
router.include_router(router_busca_global.router)

# Rotas client (usam X-Super-Token)
router.include_router(router_complementos_client)
router.include_router(router_busca_global_client)

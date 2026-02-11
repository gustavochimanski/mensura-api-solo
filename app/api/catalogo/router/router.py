from fastapi import APIRouter
from app.api.catalogo.router.admin import (
    router_produtos,
    router_combos,
    router_complementos,
    router_receitas,
    router_busca_global,
)
from app.api.catalogo.router.client import (
    router_complementos_client,
    router_combos_client,
    router_busca_global_client,
)
from app.api.catalogo.router.public import (
    router_complementos_public,
    router_combos_public,
)

router = APIRouter()

# Rotas admin (usam autenticação de admin)
router.include_router(router_produtos.router)
router.include_router(router_combos.router)
router.include_router(router_complementos.router)
router.include_router(router_receitas.router)
router.include_router(router_busca_global.router)

# Rotas client (usam X-Super-Token)
router.include_router(router_complementos_client)
router.include_router(router_combos_client.router)
router.include_router(router_busca_global_client)

# Rotas públicas (não requerem autenticação)
router.include_router(router_complementos_public)
router.include_router(router_combos_public)

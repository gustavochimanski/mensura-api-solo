from fastapi import APIRouter, Depends

from app.api.cardapio.router.public import router_home_public
from app.api.cardapio.router import router_printer_public
from app.api.cardapio.router.pagamentos import router_pagamentos_client
from app.api.cadastros.router.admin.router_cupons_admin import router as router_cupons_admin
from app.api.cardapio.router.pagamentos import router_pagamentos_admin
from app.api.cardapio.router.pagamentos import router_pagamentos_webhook
from app.api.financeiro.router.admin.router_acertos_entregadores_admin import router as router_acertos_entregadores_admin
from app.api.cardapio.router.admin.router_minio_admin import router as router_minio_admin
from app.api.cardapio.router.admin.router_categorias_admin import router as router_categorias_admin
from app.api.cardapio.router.admin.router_vitrines import router as router_vitrines_admin

api_cardapio = APIRouter(
    tags=["API - Cardápio"]
)

# Routers públicos (sem autenticação)
api_cardapio.include_router(router_printer_public.router)
api_cardapio.include_router(router_home_public.router)
api_cardapio.include_router(router_pagamentos_webhook.router)

# Routers para clientes (usam super_token)
api_cardapio.include_router(router_pagamentos_client.router)

# Routers para admin (usam get_current_user)
api_cardapio.include_router(router_cupons_admin)
api_cardapio.include_router(router_pagamentos_admin.router)
api_cardapio.include_router(router_acertos_entregadores_admin)
api_cardapio.include_router(router_minio_admin)
api_cardapio.include_router(router_categorias_admin)
api_cardapio.include_router(router_vitrines_admin)

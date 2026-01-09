# app/api/cadastros/router/router.py

from fastapi import APIRouter, Depends

from app.api.cadastros.router.admin import (
    router_categorias,
    router_clientes,
    router_entregadores,
    router_meio_pagamento,
    router_parceiros,
    router_regiao_entrega,
    router_enderecos,
)
from app.api.cadastros.router.client import (
    router_categorias as router_categorias_client,
    router_clientes as router_clientes_client,
    router_enderecos as router_enderecos_client,
    router_meio_pagamento as router_meio_pagamento_client,
)
from app.api.cadastros.router.public import (
    router_parceiros as router_parceiros_public,
)
from app.core.admin_dependencies import get_current_user

api_cadastros = APIRouter(
    tags=["API - Cadastros"]
)

# Routers públicos (sem autenticação)
api_cadastros.include_router(router_parceiros_public)

# Routers para clientes (usam super_token)
api_cadastros.include_router(router_categorias_client)
api_cadastros.include_router(router_clientes_client)
api_cadastros.include_router(router_enderecos_client)
api_cadastros.include_router(router_meio_pagamento_client)

# Routers para admin (usam get_current_user)
api_cadastros.include_router(router_categorias)
api_cadastros.include_router(router_clientes)
api_cadastros.include_router(router_entregadores)
api_cadastros.include_router(router_meio_pagamento)
api_cadastros.include_router(router_parceiros)
api_cadastros.include_router(router_regiao_entrega)
api_cadastros.include_router(router_enderecos)


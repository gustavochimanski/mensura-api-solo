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
    router_usuario,
    router_permissoes,
    router_permissoes_me,
)
from app.api.empresas.router.admin import router_empresa_admin
from app.api.cadastros.router.client import (
    router_categorias as router_categorias_client,
    router_clientes as router_clientes_client,
    router_enderecos as router_enderecos_client,
    router_meio_pagamento as router_meio_pagamento_client,
)
from app.api.cadastros.router.public import (
    router_parceiros as router_parceiros_public,
)
from app.core.admin_dependencies import require_admin
from app.core.authorization import require_any_permissions, require_permissions

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
api_cadastros.include_router(
    router_categorias,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_clientes,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_entregadores,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_meio_pagamento,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_parceiros,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_regiao_entrega,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_enderecos,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/cadastros"]))],
)
api_cadastros.include_router(
    router_usuario,
    dependencies=[
        Depends(require_admin),
        Depends(require_any_permissions(["route:/configuracoes", "route:/configuracoes:usuarios"])),
    ],
)
api_cadastros.include_router(
    router_permissoes,
    dependencies=[
        Depends(require_admin),
        Depends(require_any_permissions(["route:/configuracoes", "route:/configuracoes:permissoes"])),
    ],
)
api_cadastros.include_router(router_permissoes_me)
api_cadastros.include_router(
    router_empresa_admin,
    prefix="/api/cadastros/admin/empresas",
    tags=["Admin - Cadastros - Empresas"],
    dependencies=[
        Depends(require_admin),
        Depends(require_any_permissions(["route:/configuracoes", "route:/configuracoes:empresas"])),
    ],
)


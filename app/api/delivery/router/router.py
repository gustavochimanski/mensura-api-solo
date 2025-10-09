from fastapi import APIRouter, Depends

from app.api.delivery.router.router_home_dv import router as home_router
from app.api.delivery.router.categorias.router_categorias_dv import router as categorias_router
from app.api.delivery.router.categorias.router_categorias_admin_dv import router as categorias_admin_router
from app.api.delivery.router.client.router_client_dv import router as cliente_router
from app.api.delivery.router.client.router_client_admin_dv import router as cliente_admin_router
from app.api.delivery.router.pedidos.router_pedidos_dv import router as pedidos_router
from app.api.delivery.router.pagamentos.router_pagamentos_dv import router as pagamentos_router
from app.api.delivery.router.pedidos.router_pedidos_admin_dv import router as router_pedidos_admin
from app.api.delivery.router.pagamentos.router_pagamentos_admin_dv import router as router_pagamentos_admin
from app.api.delivery.router.router_produtos_dv import router as produtos_router
from app.api.delivery.router.router_vitrine import router as vitrines_router
from app.api.delivery.router.router_cupons_dv import router as cupons_router
from app.api.delivery.router.router_entregadores import router as entregadores_router
from app.api.delivery.router.enderecos.router_enderecos import router as enderecos_router
from app.api.delivery.router.enderecos.router_enderecos_admin_dv import router as enderecos_admin_router
from app.api.delivery.router.meio_pagamento.router_meio_pagamento import router as meio_pagamento_router
from app.api.delivery.router.meio_pagamento.router_meio_pagamento_admin_dv import router as meio_pagamento_admin_router
from app.api.delivery.router.parceiros.router_parceiros_publico import router as parceiros_publico_router
from app.api.delivery.router.parceiros.router_parceiros_admin import router as parceiros_admin_router
from app.api.delivery.router.router_regiao_entrega import router as regiao_entrega_router
from app.api.delivery.router.router_printer import router as printer_router

from app.core.admin_dependencies import get_current_user

api_delivery = APIRouter()

# Routers públicos (sem autenticação)
api_delivery.include_router(home_router)
api_delivery.include_router(parceiros_publico_router)
api_delivery.include_router(categorias_router)

# Routers para clientes (usam super_token)
api_delivery.include_router(pedidos_router)
api_delivery.include_router(pagamentos_router)
api_delivery.include_router(printer_router)
api_delivery.include_router(cliente_router)
api_delivery.include_router(enderecos_router)
api_delivery.include_router(meio_pagamento_router)

# Routers para admin (usam get_current_user)
api_delivery.include_router(router_pedidos_admin)
api_delivery.include_router(router_pagamentos_admin)
api_delivery.include_router(cliente_admin_router)
api_delivery.include_router(enderecos_admin_router)
api_delivery.include_router(meio_pagamento_admin_router)
api_delivery.include_router(categorias_admin_router)
api_delivery.include_router(parceiros_admin_router)
api_delivery.include_router(cupons_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(entregadores_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(produtos_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(regiao_entrega_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(vitrines_router, dependencies=[Depends(get_current_user)])

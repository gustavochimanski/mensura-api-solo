from fastapi import APIRouter, Depends

from app.api.delivery.router.router_home_dv import router as home_router
from app.api.delivery.router.router_categorias_dv import router as categorias_router
from app.api.delivery.router.router_cliente_dv import router as cliente_router
from app.api.delivery.router.router_pedidos_dv import router as pedidos_router
from app.api.delivery.router.router_produtos_dv import router as produtos_router
from app.api.delivery.router.router_vitrine import router as vitrines_router
from app.api.delivery.router.router_cupons_dv import router as cupons_router
from app.api.delivery.router.router_entregadores import router as entregadores_router
from app.api.delivery.router.router_enderecos import router as enderecos_router
from app.api.delivery.router.router_meio_pagamento import router as meio_pagamento_router
from app.api.delivery.router.router_parceiros import router as parceiros_router

from app.core.admin_dependencies import get_current_user

api_delivery = APIRouter()
api_delivery.include_router(home_router)
api_delivery.include_router(categorias_router)
api_delivery.include_router(cliente_router)
api_delivery.include_router(pedidos_router),
api_delivery.include_router(meio_pagamento_router)
api_delivery.include_router(produtos_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(vitrines_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(cupons_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(entregadores_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(enderecos_router)
api_delivery.include_router(parceiros_router)
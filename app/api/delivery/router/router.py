from fastapi import APIRouter, Depends

from app.api.delivery.router.cardapio_dv_router import router as cardapio_router
from app.api.delivery.router.categorias_dv_router import router as categorias_router
from app.api.delivery.router.cliente_router import router as cliente_router
from app.api.delivery.router.pedidos_dv_router import router as pedidos_router
from app.api.delivery.router.produtos_dv_router import router as produtos_router
from app.api.delivery.router.vitrine_router import router as vitrines_router
from app.api.delivery.router.cupons_router import router as cupons_router
from app.api.delivery.router.entregadores_router import router as entregadores_router
from app.api.delivery.router.enderecos_router import router as enderecos_router
from app.core.dependencies import get_current_user

api_delivery = APIRouter()
api_delivery.include_router(cardapio_router)
api_delivery.include_router(categorias_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(cliente_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(pedidos_router)
api_delivery.include_router(produtos_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(vitrines_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(cupons_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(entregadores_router, dependencies=[Depends(get_current_user)])
api_delivery.include_router(enderecos_router, dependencies=[Depends(get_current_user)])

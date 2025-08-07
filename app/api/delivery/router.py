# app/api/mensura/router.py

from fastapi import APIRouter, Depends

from app.api.delivery.controllers.cardapio_dv_controller import router as router_cardapio
from app.api.delivery.controllers.cliente_controller import router as router_clientes
from app.api.delivery.controllers.pedidos_dv_controller import router as router_pedidos
from app.api.delivery.controllers.categorias_dv_controller import router as router_categorias
from app.api.delivery.controllers.produtos_dv_controller import router as router_produtos
from app.api.delivery.controllers.vitrine_controller import router as router_vitrines
from app.core.dependencies import get_current_user

router = APIRouter()

router.include_router(router_cardapio)
router.include_router(router_clientes)
router.include_router(router_pedidos)
router.include_router(router_categorias, dependencies=[Depends(get_current_user)])
router.include_router(router_produtos, dependencies=[Depends(get_current_user)])
router.include_router(router_vitrines, dependencies=[Depends(get_current_user)])

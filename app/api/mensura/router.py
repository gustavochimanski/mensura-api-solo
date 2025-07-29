# app/api/mensura/router.py

from fastapi import APIRouter, Depends

from app.api.mensura.controllers.categorias_dv_controller import router as routerCategoriasDelivery
from app.api.mensura.controllers.produtos_dv_controller import router as routerProdutosDelivery
from app.api.mensura.controllers.cardapio_dv_controller import router as routerCardapio
from app.api.mensura.controllers.vitrine_controller import router as routerSubCategorias
from app.core.dependencies import get_current_user

router = APIRouter()

router.include_router(routerCardapio)
router.include_router(routerProdutosDelivery, dependencies=[Depends(get_current_user)])
router.include_router(routerCategoriasDelivery, dependencies=[Depends(get_current_user)])
router.include_router(routerSubCategorias, dependencies=[Depends(get_current_user)])

# app/api/public/router.py
from fastapi import APIRouter
from app.api.public.controllers.empresas.getEmpresasController import router as empresasRouter
from app.api.public.controllers.produtos.produtosPublicController import router as produtosPublicRouter

router = APIRouter(tags=["Public"])

router.include_router(empresasRouter)
router.include_router(produtosPublicRouter)
# app/api/BI/router.py
from fastapi import APIRouter

from app.api.BI.controllers.metas.router import router as metas_router
from app.api.BI.controllers.dashboard.router import router as dashboard_router
from app.api.BI.controllers.compras.router import router as compras_router
from app.api.BI.controllers.vendas.router import router as vendas_router

router = APIRouter(tags=["BI"])
router.include_router(metas_router)
router.include_router(dashboard_router)
router.include_router(compras_router)
router.include_router(vendas_router, prefix="/vendas", tags=["Vendas"])

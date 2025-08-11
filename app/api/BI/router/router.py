# app/api/BI/router.py
from fastapi import APIRouter

from app.api.BI.router.router_compras import router as router_compras
from app.api.BI.router.router_dashboard import router as router_dashboard
from app.api.BI.router.router_metas import router as router_metas
from app.api.BI.router.router_vendas import router as router_vendas

router = APIRouter(tags=["BI"])
router.include_router(router_compras)
router.include_router(router_dashboard)
router.include_router(router_metas)
router.include_router(router_vendas)

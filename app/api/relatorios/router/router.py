# app/api/relatorios/router/router.py
from fastapi import APIRouter

# Router principal que agrupa todos os routers de relatórios
router = APIRouter(
    tags=["API - Relatórios"]
)

# Inclui os routers específicos de relatórios
from .admin import router as admin_router
router.include_router(admin_router)

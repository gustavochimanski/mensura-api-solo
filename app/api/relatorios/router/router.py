# app/api/relatorios/router/router.py
from fastapi import APIRouter
from app.api.relatorios.router.admin.router import router as admin_router

# Router principal que agrupa todos os routers de relatórios
router = APIRouter()

# Inclui os routers específicos
router.include_router(admin_router)

from fastapi import APIRouter

from .comprasController import router as compras_router

router = APIRouter()

router.include_router(compras_router)
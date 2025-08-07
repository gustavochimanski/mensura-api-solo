from fastapi import APIRouter

from .resumoVendasController import router as resumoVendasRouter
from .vendaPorHoraController import router as vendaPorHoraRouter

router = APIRouter()

router.include_router(resumoVendasRouter)
router.include_router(vendaPorHoraRouter)


from fastapi import APIRouter

from .resumoVendasController import router as resumoVendasRouter
from .vendaDetalhadaController import router as vendaDetalhaRouter
from .vendaPorHoraController import router as vendaPorHoraRouter

router = APIRouter()

router.include_router(resumoVendasRouter)
router.include_router(vendaDetalhaRouter)
router.include_router(vendaPorHoraRouter)


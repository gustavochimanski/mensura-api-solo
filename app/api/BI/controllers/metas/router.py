from fastapi import APIRouter

from .metasController import router as metasRouter
from .gerarMetasController import router as gerarMetasRouter
router = APIRouter()

router.include_router(metasRouter)
router.include_router(gerarMetasRouter)

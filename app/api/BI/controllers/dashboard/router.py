from fastapi import APIRouter

from .dashboardController import router as dashboardRouter

router = APIRouter()

router.include_router(dashboardRouter)
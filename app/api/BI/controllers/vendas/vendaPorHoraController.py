# app/router/relatorios/vendaPorHoraController.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.BI.schemas.dashboard_types import TypeDashboardRequest
from app.database.db_connection import get_db
from app.api.BI.schemas.vendas.vendasPorHoraTypes import TypeVendaPorHoraResponse
from app.api.BI.services.vendas.vendaPorHoraService import consultaVendaPorHoraService

router = APIRouter()

@router.post("/por-hora", summary="Venda por hora", response_model=TypeVendaPorHoraResponse)
def consultaVendaPorHoraController(
    request: TypeDashboardRequest,
    db: Session = Depends(get_db)
):
    return consultaVendaPorHoraService(db, request)

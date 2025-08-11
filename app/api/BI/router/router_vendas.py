from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.schemas.dashboard_types import TypeDashboardRequest
from app.api.BI.schemas.vendas.vendasPorHoraTypes import TypeVendaPorHoraResponse
from app.api.BI.services.vendas.resumoVendasService import resumoDeVendasService
from app.api.BI.schemas.vendas.resumoVendas import  TypeResumoVendasResponse
from app.api.BI.services.vendas.vendaPorHoraService import consultaVendaPorHoraService
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(tags=["Vendas"], prefix="/api/bi/vendas")


@router.post(
    "/periodo",
    summary="Resumo vendas Periodo",
    response_model=TypeResumoVendasResponse
)
def resumoVendasController(
        request: TypeDashboardRequest,
        db: Session = Depends(get_db),  # injeta a sessão aqui
):
    logger.info(f"Request recebido: empresas={request.empresas}, inicio={request.dataInicio}, fim={request.dataFinal}")

    resultados = resumoDeVendasService(request, db)  # passa o db pro service
    if resultados is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar os dados de relatórios.")

    logger.info(f"Consulta total de relatórios geral: {resultados}")
    return resultados


@router.post("/por-hora", summary="Venda por hora", response_model=TypeVendaPorHoraResponse)
def consultaVendaPorHoraController(
    request: TypeDashboardRequest,
    db: Session = Depends(get_db)
):
    return consultaVendaPorHoraService(db, request)

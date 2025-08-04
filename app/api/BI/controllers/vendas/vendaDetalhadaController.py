from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.schemas.dashboard_types import TypeDashboardRequest
from app.database.db_connection import get_db

from app.api.BI.schemas.vendas.vendaDetalhadaTypes import (
    TypeVendaDetalhadaResponse,
)
from app.api.BI.services.vendas.vendaDetalhadaService import consultaVendaDetalhadaGeralService

import logging

from app.utils.logger import logger

router = APIRouter()

@router.post(
    summary="Consulta venda Detalhada",
    response_model=TypeVendaDetalhadaResponse,
    path="/venda-detalhada"
)
def consultaVendaDetalhadaController(
    request: TypeDashboardRequest,
    db: Session = Depends(get_db)  # ✅ injeta a sessão
):
    try:
        resultado = consultaVendaDetalhadaGeralService(request, db)
        if resultado is None:
            raise HTTPException(status_code=500, detail="Erro ao consultar venda detalhada")
        return resultado
    except Exception as e:
        logger.exception("Erro ao processar venda detalhada:")
        raise HTTPException(status_code=500, detail=str(e))

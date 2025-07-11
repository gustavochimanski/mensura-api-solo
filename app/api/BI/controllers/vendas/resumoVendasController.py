from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.services.vendas.resumoVendasService import resumoDeVendasService
from app.api.BI.schemas.vendas.resumoVendas import TypeVendasPeriodoGeral, TypeResumoVendasResponse
from app.database.db_connection import get_db  # importa o get_db correto
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/periodo",
    summary="Resumo vendas Periodo",
    response_model=TypeResumoVendasResponse
)
def resumoVendasController(
        request: TypeVendasPeriodoGeral,
        db: Session = Depends(get_db),  # injeta a sessão aqui
):
    logger.info(f"Request recebido: empresas={request.empresas}, inicio={request.dataInicio}, fim={request.dataFinal}")

    resultados = resumoDeVendasService(request, db)  # passa o db pro service
    if resultados is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar os dados de relatórios.")

    logger.info(f"Consulta total de relatórios geral: {resultados}")
    return resultados

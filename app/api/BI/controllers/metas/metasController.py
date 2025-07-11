from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.BI.services.metas.InserirMetasService import salvar_ou_atualizar_meta
from app.api.BI.schemas.metas_types import (
    TypeConsultaMetaRequest,
    TypeDashboardMetaReturn,
    TypeInserirMetaRequest,
)
from app.api.BI.services.metas.consultaMetasService import consultar_metas_periodo
from app.utils.logger import logger

router = APIRouter( tags=["Metas"])

# 🚀 AGORA É POST
@router.post("/metas/periodo", response_model=TypeDashboardMetaReturn, summary="Consulta Metas  Período")
def obter_total_metas_geral(
    request: TypeConsultaMetaRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"POST /metas/periodo recebido: empresas={request.empresas}, inicio={request.dataInicio}, fim={request.dataFinal}")

    resultados = consultar_metas_periodo(request, db)

    if resultados is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar as metas.")

    return resultados


@router.post("/metas/insert", summary="Inserir Meta por tipo e data")
def inserir_meta_controller(request: TypeInserirMetaRequest, db: Session = Depends(get_db)):
    return {"mensagem": salvar_ou_atualizar_meta(request, db)}

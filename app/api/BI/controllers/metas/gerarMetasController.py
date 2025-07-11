from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from typing import List

from app.database.db_connection import get_db
from app.api.BI.schemas.metas_types import MetasEmpresa, TypeConsultaMetaRequest
from app.api.BI.services.metas.gerarMetaVendaService import gerarMetaVendaService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/gerar-venda", response_model=List[MetasEmpresa], summary="Gerar metas de venda (metaVenda) com base no histórico")
def gerar_meta_venda_controller(
    request: TypeConsultaMetaRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"POST /metas/gerar-venda recebido: empresas={request.empresas}, início={request.dataInicio}, fim={request.dataFinal}")
    fator = request.fatorCrescimento / 100
    try:
        resultado = gerarMetaVendaService(
            session=db,
            dataInicial=request.dataInicio,
            dataFinal=request.dataFinal,
            empresas=request.empresas,
            fator_crescimento=fator
        )
        return resultado

    except Exception as e:
        logger.error(f"Erro ao gerar metas de venda: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar metas de venda.")

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.services.metas.gerarMetaVendaService import gerarMetaVendaService
from app.database.db_connection import get_db
from app.api.BI.services.metas.InserirMetasService import salvar_ou_atualizar_meta
from app.api.BI.schemas.metas_types import (
    TypeConsultaMetaRequest,
    TypeDashboardMetaReturn,
    TypeInserirMetaRequest, MetasEmpresa,
)
from app.api.BI.services.metas.consultaMetasService import consultar_metas_periodo
from app.utils.logger import logger

router = APIRouter( tags=["Metas"], prefix="/api/bi/metas")

# 🚀 AGORA É POST
@router.post("/periodo", response_model=TypeDashboardMetaReturn, summary="Consulta Metas  Período")
def obter_total_metas_geral(
    request: TypeConsultaMetaRequest,
    db: Session = Depends(get_db)
):
    resultados = consultar_metas_periodo(request, db)

    if resultados is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar as metas.")

    return resultados


@router.post("/insert", summary="Inserir Meta por tipo e data")
def inserir_meta_controller(request: TypeInserirMetaRequest, db: Session = Depends(get_db)):
    return {"mensagem": salvar_ou_atualizar_meta(request, db)}


@router.post("/gerar-venda", response_model=List[MetasEmpresa], summary="Gerar metas de venda (metaVenda) com base no histórico")
def gerar_meta_venda_controller(
    request: TypeConsultaMetaRequest,
    db: Session = Depends(get_db)
):
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

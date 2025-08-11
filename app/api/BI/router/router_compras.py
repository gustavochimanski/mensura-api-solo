from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.services.compras.resumoDeCompras import calcular_movimento_multi
from app.api.BI.schemas.compras_types import (
    ConsultaMovimentoCompraRequest,
    ConsultaMovimentoCompraResponse
)
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(tags=["Compras"], prefix="/api/bi/compras")

@router.post(
    "/consulta_movimento",
    response_model=ConsultaMovimentoCompraResponse,
    summary="Resumo Compras Empresa"
)
def handle_consulta_movimento_compra(
    req: ConsultaMovimentoCompraRequest,
    db: Session = Depends(get_db)
) -> ConsultaMovimentoCompraResponse:
    """
    Endpoint para consultar movimentos de compra:
    - Recebe datas e lista de empresas.
    - Injetamos a sessão do DB via Depends(get_db).
    - Encaminha para o service e trata exceções.
    """
    try:
        return calcular_movimento_multi(db, req)
    except HTTPException:
        # Propaga HTTPException do service
        raise
    except Exception as e:
        logger.error(f"Erro interno ao consultar movimento de compras: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao consultar movimento de compras"
        )

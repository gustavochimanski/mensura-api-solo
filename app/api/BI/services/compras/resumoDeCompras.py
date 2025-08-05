import logging
from datetime import datetime
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.BI.repositories.compras.resumoDeComprasRepo import fetch_valores_por_empresa_multi
from app.api.BI.schemas.compras_types import (
    ConsultaMovimentoCompraRequest,
    ConsultaMovimentoCompraResponse,
    ConsultaMovimentoTotalEmpresa
)

logger = logging.getLogger(__name__)

def _meses_entre(data_inicio, data_fim) -> List[str]:
    meses, cur, ultimo = [], data_inicio.replace(day=1), data_fim.replace(day=1)
    while cur <= ultimo:
        meses.append(f"{cur.year}{cur.month:02d}")
        next_month = (cur.month % 12) + 1
        next_year = cur.year + (1 if next_month == 1 else 0)
        cur = cur.replace(year=next_year, month=next_month)
    return meses

def calcular_movimento_multi(
    db: Session,
    req: ConsultaMovimentoCompraRequest
) -> ConsultaMovimentoCompraResponse:
    # 1) Valida datas
    try:
        di = datetime.strptime(req.dataInicio, "%Y-%m-%d").date()
        df = datetime.strptime(req.dataFinal, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "datas devem ser YYYY-MM-DD")
    if df < di:
        raise HTTPException(400, "dataFinal deve ser >= dataInicio")

    # 2) Gera meses e busca resultados
    meses = _meses_entre(di, df)
    resultados = fetch_valores_por_empresa_multi(db, meses, req.empresas, di, df)

    # 3) Se não vier resultado, fallback para zero
    if not resultados:
        por_empresa = [
            ConsultaMovimentoTotalEmpresa(empresa=emp, valorTotal=0.0)
            for emp in req.empresas
        ]
    else:
        por_empresa = [
            ConsultaMovimentoTotalEmpresa(empresa=cod, valorTotal=valor)
            for cod, valor in resultados
        ]

    total_geral = sum(item.valorTotal for item in por_empresa)

    return ConsultaMovimentoCompraResponse(
        por_empresa=por_empresa,
        total_geral=total_geral
    )

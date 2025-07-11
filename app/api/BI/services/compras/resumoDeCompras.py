# app/services/compras/resumoDeComprasRepo.py
from datetime import datetime, date
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.BI.repositories.compras.resumoDeComprasRepo import fetch_valores_por_empresa_multi
from app.api.BI.schemas.compras_types import (
    ConsultaMovimentoCompraRequest,
    ConsultaMovimentoCompraResponse,
    ConsultaMovimentoTotalEmpresa
)

def _meses_entre(data_inicio: date, data_fim: date) -> List[str]:
    meses, cur, ultimo = [], data_inicio.replace(day=1), data_fim.replace(day=1)
    while cur <= ultimo:
        meses.append(f"{cur.year}{cur.month:02d}")
        cur = cur.replace(year=cur.year + (cur.month//12), month=(cur.month % 12) + 1)
    return meses

def calcular_movimento_multi(
    db: Session,
    req: ConsultaMovimentoCompraRequest
) -> ConsultaMovimentoCompraResponse:
    try:
        di = datetime.strptime(req.dataInicio, "%Y-%m-%d").date()
        df = datetime.strptime(req.dataFinal, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "datas devem ser YYYY-MM-DD")
    if df < di:
        raise HTTPException(400, "dataFinal deve ser >= dataInicio")

    meses = _meses_entre(di, df)
    resultados = fetch_valores_por_empresa_multi(db, meses, req.empresas, di, df)

    por_empresa = [
        ConsultaMovimentoTotalEmpresa(empresa=cod, valorTotal=valor)
        for cod, valor in resultados
    ]
    total_geral = sum(item.valorTotal for item in por_empresa)
    return ConsultaMovimentoCompraResponse(por_empresa=por_empresa, total_geral=total_geral)

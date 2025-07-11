# app/services/compras/compraDetalhadaService.py
from datetime import datetime, date, timedelta
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.BI.schemas.compras_types import (
    CompraDetalhadaByDate,
    CompraDetalhadaEmpresas,
    CompraDetalhadaResponse,
    ConsultaMovimentoCompraRequest,
)
from app.api.BI.repositories.compras.compraDetalhadaRepo import compraDetalhadaByDayRepo

def _meses_entre(data_inicio: date, data_fim: date) -> List[str]:
    meses, cur, ultimo = [], data_inicio.replace(day=1), data_fim.replace(day=1)
    while cur <= ultimo:
        meses.append(f"{cur.year}{cur.month:02d}")
        cur = cur.replace(year=cur.year + (cur.month // 12), month=(cur.month % 12) + 1)
    return meses

def compraDetalhadaService(
    db: Session,
    req: ConsultaMovimentoCompraRequest
) -> CompraDetalhadaResponse:
    try:
        di = datetime.strptime(req.dataInicio, "%Y-%m-%d").date()
        df = datetime.strptime(req.dataFinal, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "datas devem ser YYYY-MM-DD")
    if df < di:
        raise HTTPException(400, "dataFinal deve ser >= dataInicio")

    # gera os dias do período
    dias = []
    cur = di
    while cur <= df:
        dias.append(cur)
        cur += timedelta(days=1)

    meses = _meses_entre(di, df)

    # estrutura: {empresa: {data: valor}}
    mapa = {emp: {d: 0.0 for d in dias} for emp in req.empresas}

    for mes in meses:
        resultados = compraDetalhadaByDayRepo(
            db=db,
            mes=mes,
            empresas=req.empresas,
            data_inicio=di,
            data_fim=df
        )
        for empresa, data, soma in resultados:
            if data in mapa[empresa]:
                mapa[empresa][data] += float(soma or 0)

    compra_empresas = []
    for empresa, valores_por_data in mapa.items():
        dates = [
            CompraDetalhadaByDate(data=d, valor=valores_por_data[d])
            for d in sorted(valores_por_data)
        ]
        compra_empresas.append(CompraDetalhadaEmpresas(empresa=empresa, dates=dates))

    return CompraDetalhadaResponse(
        empresas=req.empresas,
        dataInicio=di,
        dataFinal=df,
        compraEmpresas=compra_empresas
    )

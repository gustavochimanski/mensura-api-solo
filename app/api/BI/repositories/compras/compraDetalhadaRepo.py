# app/repositories/consultaMovimentoCompraRepo.py
from sqlalchemy import Table, MetaData, select, func
from sqlalchemy.orm import Session
from typing import List, Tuple
from datetime import date

TIPOS_VALIDOS = ["PC", "TE", "TS", "BR"]

def compraDetalhadaByDayRepo(
    db: Session,
    mes: str,
    empresas: List[str],
    data_inicio: date,
    data_fim: date
) -> List[Tuple[str, date, float]]:
    """
    Retorna (empresa, data, soma) para cada data do mês na tabela lpd{YYYYMM}.
    """
    metadata = MetaData()
    metadata.bind = db.get_bind()
    tabela = Table(
        f"lpd{mes}", metadata,
        autoload_with=metadata.bind,
        schema="public"
    )

    query = (
        select(
            tabela.c.lcpd_codempresa.label("empresa"),
            func.date(tabela.c.lcpd_dtmvto).label("data"),
            func.sum(tabela.c.lcpd_valor).label("soma")
        )
        .where(tabela.c.lcpd_tipoprocesso.in_(TIPOS_VALIDOS))
        .where(tabela.c.lcpd_codempresa.in_(empresas))
        .where(tabela.c.lcpd_dtmvto.between(data_inicio, data_fim))
        .group_by(tabela.c.lcpd_codempresa, func.date(tabela.c.lcpd_dtmvto))
    )

    return db.query.all()

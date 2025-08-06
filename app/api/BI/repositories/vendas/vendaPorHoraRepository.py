from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.pdv.models.lctoprodutos_pdv_model import LctoProdutosPDV

def consultaVendaPorHoraRepository(
    db: Session,
    dataInicio: str,
    dataFinal: str,
    empresas: list[str],
    status_venda: Optional[str] = None,
    situacao: Optional[str] = None
) -> list:
    """
    Consulta vendas por hora agrupadas por empresa e hora,
    retornando total de cupons, total vendido e ticket médio.
    """
    hora_convertida = func.date_part('hour', LctoProdutosPDV.lcpr_datahoraemiss)

    query = db.query(
        LctoProdutosPDV.lcpr_codempresa.label("empresa"),
        hora_convertida.label("hora"),
        func.count(func.distinct(LctoProdutosPDV.lcpr_cupom)).label("total_cupons"),
        func.sum(LctoProdutosPDV.lcpr_totalprodutos).label("total_vendas"),
        func.avg(LctoProdutosPDV.lcpr_totalprodutos).label("ticket_medio")
    ).filter(
        LctoProdutosPDV.lcpr_datamvto.between(dataInicio, dataFinal),
        LctoProdutosPDV.lcpr_codempresa.in_(empresas),
    )

    if status_venda:
        query = query.filter(LctoProdutosPDV.lcpr_statusvenda == status_venda)
    if situacao:
        query = query.filter(LctoProdutosPDV.lcpr_situacao == situacao)

    return (
        query
        .group_by(LctoProdutosPDV.lcpr_codempresa, hora_convertida)
        .order_by(LctoProdutosPDV.lcpr_codempresa, hora_convertida)
        .all()
    )

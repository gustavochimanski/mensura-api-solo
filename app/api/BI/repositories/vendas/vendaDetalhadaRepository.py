from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.public.models.lcto.lctoprodutos_model import LctoProdutosPUBLIC

def  consultaVendaDetalhadaRepository(
        db: Session,
        empresa: str,
        dataInicio: date,
        dataFinal: date,
) -> list[tuple[date, float]]:

    rows = (db.query(
                LctoProdutosPUBLIC.lcpr_dtmvto.label("data"),
                func.sum(
                    LctoProdutosPUBLIC.lcpr_totalprodutos
                    - LctoProdutosPUBLIC.lcpr_desconto
                    + LctoProdutosPUBLIC.lcpr_acrescimopdv
                ).label("total")
            )
            .filter(LctoProdutosPUBLIC.lcpr_codempresa == empresa)
            .filter(LctoProdutosPUBLIC.lcpr_dtmvto.between(dataInicio, dataFinal))
            .group_by(LctoProdutosPUBLIC.lcpr_dtmvto)
            .order_by(LctoProdutosPUBLIC.lcpr_dtmvto)
            .all())
    """
    Devolve [(date, total_venda)].
    """
    return [(r.data, float(r.total)) for r in rows]


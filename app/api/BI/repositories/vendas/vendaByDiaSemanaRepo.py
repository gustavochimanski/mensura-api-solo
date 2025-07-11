import logging
from datetime import date, timedelta
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_

from app.api.pdv.models.lctoprodutos_pdv_model import LctoProdutosPDV

logger = logging.getLogger(__name__)
NOME_REQUISICAO = "POST /metas/gerar-venda"

def buscar_vendas_por_dia_semana(session: Session, empresa: str, referencia: date, semanas: int = 3) -> List[float]:
    vendas: List[float] = []

    datas_referencia = [referencia - timedelta(weeks=i) for i in range(1, semanas + 1)]

    logger.info(
        f"[{NOME_REQUISICAO}] 🔍 Buscando vendas semanais para {empresa} nas datas: "
        f"{[d.strftime('%Y-%m-%d') for d in datas_referencia]}"
    )

    for data_ref in datas_referencia:
        try:
            stmt = (
                select(func.sum(LctoProdutosPDV.lcpr_totaldcto))
                .where(
                    and_(
                        LctoProdutosPDV.lcpr_codempresa == empresa,
                        LctoProdutosPDV.lcpr_datamvto == data_ref,
                    )
                )
            )
            result = session.execute(stmt).scalar()
            valor = float(result or 0)
            vendas.append(valor)
        except Exception as e:
            logger.error(
                f"[{NOME_REQUISICAO}] ❌ Erro ao buscar venda para {empresa} em {data_ref.strftime('%Y-%m-%d')}: {e}"
            )
            vendas.append(0)

    return vendas

import logging
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_
from app.api.pdv.models.lctoprodutos_pdv_model import LctoProdutosPDV

logger = logging.getLogger(__name__)

def buscar_vendas_dia(session: Session, empresa: str, dia: date) -> list[float]:
    nome_requisicao = "POST /metas/gerar-venda"
    ano_anterior = dia.year - 1
    data_ref = dia.replace(year=ano_anterior)
    vendas: list[float] = []

    logger.info(
        f"[{nome_requisicao}] 🎯 Buscando venda para empresa '{empresa}' em {data_ref.strftime('%Y-%m-%d')} (mesmo dia do ano anterior)"
    )

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

        logger.info(
            f"[{nome_requisicao}] ✅ Venda encontrada para '{empresa}' em {data_ref}: R${valor:,.2f}"
        )

    except Exception as e:
        logger.error(
            f"[{nome_requisicao}] ❌ Erro ao buscar venda para {data_ref.strftime('%Y-%m-%d')}: {e}"
        )
        vendas.append(0)

    return vendas

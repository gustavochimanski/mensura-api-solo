# app/api/BI/repositories/compras/resumoDeComprasRepo.py
import logging
from typing import List, Tuple
from sqlalchemy import Table, MetaData, select, func, union_all, inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
TIPOS_VALIDOS = ["PC", "TE", "TS", "BR"]

def fetch_valores_por_empresa_multi(
    db: Session,
    lista_meses: List[str],
    empresas: List[str],
    data_inicio,
    data_fim
) -> List[Tuple[str, float]]:
    """
    Para cada mês em lista_meses, carrega a tabela 'lpdYYYYMM',
    filtra por tipo, data e empresa, soma valor por empresa.
    Faz UNION ALL de todas as subconsultas e agrupa por empresa.
    """
    logger.info(f"[Compras•Repo] Empresas no filtro: {empresas}")
    logger.info(f"[Compras•Repo] Meses calculados: {lista_meses}")

    insp = inspect(db.get_bind())
    tabelas_disponiveis = insp.get_table_names(schema="public")
    logger.info(f"[Compras•Repo] Tabelas em public: {tabelas_disponiveis}")

    metadata = MetaData(bind=db.get_bind())
    consultas = []

    for mes in lista_meses:
        nome_tabela = f"lpd{mes}"
        if nome_tabela not in tabelas_disponiveis:
            logger.warning(f"[Compras•Repo] Tabela não encontrada, pulando: {nome_tabela}")
            continue

        tabela = Table(nome_tabela, metadata, autoload_with=metadata.bind, schema="public")
        q = (
            select(
                tabela.c.lcpd_codempresa.label("empresa"),
                func.sum(tabela.c.lcpd_valor).label("soma"),
            )
            .where(tabela.c.lcpd_tipoprocesso.in_(TIPOS_VALIDOS))
            .where(tabela.c.lcpd_dtmvto >= data_inicio)
            .where(tabela.c.lcpd_dtmvto <= data_fim)
            .where(tabela.c.lcpd_codempresa.in_(empresas))
            .group_by(tabela.c.lcpd_codempresa)
        )
        consultas.append(q)

    if not consultas:
        logger.warning("[Compras•Repo] Nenhuma consulta SQL gerada — nenhum mês/tabela válida.")
        return []

    union = union_all(*consultas).alias("u")
    final = (
        select(
            union.c.empresa,
            func.sum(union.c.soma).label("soma_total")
        )
        .group_by(union.c.empresa)
        .order_by(union.c.empresa)
    )

    resultados = db.execute(final).all()
    logger.info(f"[Compras•Repo] Resultados brutos: {resultados}")
    return [(row.empresa, float(row.soma_total or 0)) for row in resultados]

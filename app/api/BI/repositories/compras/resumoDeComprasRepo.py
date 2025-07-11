import logging
from sqlalchemy import Table, MetaData, select, func, union_all
from sqlalchemy.orm import Session
from typing import List, Tuple

# Configuração básica do logger
logger = logging.getLogger(__name__)

# Você pode configurar handler e formato se quiser logar em arquivo, etc

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
    logger.info("Iniciando fetch_valores_por_empresa_multi")
    logger.info(f"Meses: {lista_meses}, Empresas: {empresas}, Período: {data_inicio} a {data_fim}")

    metadata = MetaData()
    metadata.bind = db.get_bind()

    consultas = []
    for mes in lista_meses:
        nome_tabela = f"lpd{mes}"
        logger.info(f"Carregando tabela: {nome_tabela}")
        try:
            tabela = Table(
                nome_tabela,
                metadata,
                autoload_with=metadata.bind,
                schema="public"
            )
        except Exception as e:
            logger.error(f"Erro ao carregar a tabela {nome_tabela}: {e}")
            continue

        q = (
            select(
                tabela.c.lcpd_codempresa.label("empresa"),
                func.sum(tabela.c.lcpd_valor).label("soma")
            )
            .where(tabela.c.lcpd_tipoprocesso.in_(TIPOS_VALIDOS))
            .where(tabela.c.lcpd_dtmvto >= data_inicio)
            .where(tabela.c.lcpd_dtmvto <= data_fim)
            .where(tabela.c.lcpd_codempresa.in_(empresas))
            .group_by(tabela.c.lcpd_codempresa)
        )
        consultas.append(q)

    if not consultas:
        logger.warning("Nenhuma consulta gerada. Retornando lista vazia.")
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

    try:
        resultados = db.execute(final).all()
        logger.info(f"Consulta final retornou {len(resultados)} resultados.")
        return [(row.empresa, float(row.soma_total or 0)) for row in resultados]
    except Exception as e:
        logger.error(f"Erro ao executar consulta final: {e}")
        return []

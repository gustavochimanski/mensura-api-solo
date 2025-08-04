import re
from sqlalchemy import Table, MetaData, Column
from sqlalchemy.orm import declarative_base
from app.database.db_connection import engine

Base = declarative_base()
_model_cache = {}

def get_lpd_model(ano_mes: str):
    if not re.match(r"^\d{6}$", ano_mes):
        raise ValueError("Formato inválido: use 'yyyymm', ex: '202501'")

    nome_tabela = f"lpd{ano_mes}"

    if nome_tabela in _model_cache:
        return _model_cache[nome_tabela]

    metadata = MetaData(schema="public")

    # carrega estrutura original
    raw_table = Table(nome_tabela, metadata, autoload_with=engine)

    if "lcpd_seq" not in raw_table.columns:
        raise RuntimeError(f"Tabela {nome_tabela} não possui coluna 'lcpd_seq'.")

    # recria a tabela com a PK definida manualmente
    tabela = Table(
        nome_tabela,
        metadata,
        *[
            Column(col.name, col.type, primary_key=(col.name == "lcpd_seq"))
            for col in raw_table.columns
        ],
        schema="public",
        extend_existing=True  # 👈 isso resolve o erro
    )

    model = type(
        f"Lpd{ano_mes}Model",
        (Base,),
        {
            "__table__": tabela,
            "__tablename__": nome_tabela,
            "__table_args__": {"schema": "public"}
        }
    )

    _model_cache[nome_tabela] = model
    return model

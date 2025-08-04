from sqlalchemy import Table, MetaData
from sqlalchemy.orm import declarative_base
from app.database.db_connection import engine
import re

Base = declarative_base()

_model_cache = {}

def get_lpd_model(ano_mes: str):
    """
    Retorna um modelo ORM dinâmico para uma tabela `lpdYYYYMM`
    Exemplo: ano_mes="202501" → tabela "lpd202501"
    """
    if not re.match(r"^\d{6}$", ano_mes):
        raise ValueError("Formato inválido: use 'yyyymm', ex: '202501'")

    nome_tabela = f"lpd{ano_mes}"  # Ex: lpd202501

    if nome_tabela in _model_cache:
        return _model_cache[nome_tabela]

    metadata = MetaData(schema="public")
    tabela = Table(
        nome_tabela,
        metadata,
        autoload_with=engine
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

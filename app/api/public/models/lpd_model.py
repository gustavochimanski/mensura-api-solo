import re
from sqlalchemy import Table, MetaData
from sqlalchemy.orm import declarative_base
from app.database.db_connection import engine

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

    # Retorna do cache se já foi criado antes
    if nome_tabela in _model_cache:
        return _model_cache[nome_tabela]

    # Cria metadata e carrega a tabela do banco
    metadata = MetaData(schema="public")
    tabela = Table(
        nome_tabela,
        metadata,
        autoload_with=engine
    )

    # Define uma chave primária fictícia apenas para o SQLAlchemy funcionar
    if "lcpd_seq" in tabela.columns:
        tabela.columns["lcpd_seq"].primary_key = True
    else:
        raise RuntimeError(f"Tabela {nome_tabela} não possui coluna lcpd_seq para usar como PK fictícia.")

    # Cria dinamicamente a classe do model
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

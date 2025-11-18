"""Criação e gerenciamento de schemas do PostgreSQL."""
import logging
from sqlalchemy import text, quoted_name
from ..db_connection import engine

logger = logging.getLogger(__name__)

# Lista de schemas gerenciados pela aplicação
SCHEMAS = [
    "mesas",
    "notifications",
    "balcao",
    "cadastros",
    "cardapio",
    "receitas",
    "produtos",
    "financeiro",
    "pedidos"
]


def criar_schemas():
    """
    Cria todos os schemas necessários para os domínios.
    
    Raises:
        Exception: Se houver erro ao criar algum schema (exceto se já existir).
    """
    try:
        with engine.begin() as conn:
            for schema in SCHEMAS:
                logger.info(f"🛠️ Criando/verificando schema: {schema}")
                try:
                    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {quoted_name(schema, quote=True)}'))
                except Exception as schema_error:
                    # Se for erro de schema já existente, apenas avisa (não é crítico)
                    if "already exists" in str(schema_error) or "duplicate key value violates unique constraint" in str(schema_error):
                        logger.info(f"ℹ️ Schema {schema} já existe (pulando)")
                    else:
                        logger.error(f"❌ Erro ao criar schema {schema}: {schema_error}")
                        raise schema_error
        logger.info("✅ Todos os schemas verificados/criados.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar schemas: {e}")
        raise


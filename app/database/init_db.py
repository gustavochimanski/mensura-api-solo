import logging
from sqlalchemy import text, quoted_name
from .db_connection import engine, Base

logger = logging.getLogger(__name__)
SCHEMAS = ["mensura", "bi", "pdv", "delivery"]

def criar_schemas():
    try:
        with engine.begin() as conn:
            for schema in SCHEMAS:
                logger.info(f"🛠️ Criando/verificando schema: {schema}")
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {quoted_name(schema, quote=True)}'))
        logger.info("✅ Todos os schemas verificados/criados.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar schemas: {e}")


def importar_models():
    pass


def criar_tabelas():
    try:
        importar_models()
        # Agora o SQLAlchemy sabe de todas as tabelas
        Base.metadata.create_all(bind=engine)

        logger.info("✅ Tabelas criadas com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")

def inicializar_banco():
    logger.info("🔹 Criando schemas...")
    criar_schemas()
    logger.info("🔹 Criando tabelas...")
    criar_tabelas()
    logger.info("✅ Banco inicializado com sucesso.")


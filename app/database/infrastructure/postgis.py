"""Configuração da extensão PostGIS do PostgreSQL."""
import logging
from sqlalchemy import text, quoted_name
from ..db_connection import engine

logger = logging.getLogger(__name__)


def remover_esquemas_postgis_desnecessarios():
    """Remove esquemas do PostGIS que não são necessários (topology, tiger, tiger_data)"""
    esquemas_para_remover = ["topology", "tiger", "tiger_data"]
    
    try:
        with engine.begin() as conn:
            for schema in esquemas_para_remover:
                try:
                    # Verifica se o schema existe antes de tentar remover
                    result = conn.execute(text("""
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = :schema_name
                    """), {"schema_name": schema})
                    
                    if result.scalar():
                        conn.execute(text(f"DROP SCHEMA IF EXISTS {quoted_name(schema, quote=True)} CASCADE"))
                        logger.info(f"✅ Schema {schema} removido com sucesso")
                    else:
                        logger.info(f"ℹ️ Schema {schema} não existe (pulando)")
                except Exception as schema_error:
                    # Não é crítico se falhar, apenas loga o aviso
                    logger.warning(f"⚠️ Erro ao remover schema {schema}: {schema_error}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao remover esquemas PostGIS desnecessários: {e}")


def habilitar_postgis():
    """
    Habilita a extensão PostGIS necessária para Geography/Geometry e valida sua disponibilidade.
    
    Raises:
        RuntimeError: Se PostGIS não estiver disponível após tentativa de criação.
    """
    logger.info("🗺️ Verificando/Habilitando extensão PostGIS...")
    
    # 1) Garante schema public
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
    except Exception as e:
        logger.warning(f"⚠️ Erro ao garantir schema public: {e}")

    # 2) Tenta criar a extensão explicitando o schema
    try:
        with engine.begin() as conn:
            # Define search_path para evitar "no schema has been selected to create in"
            conn.execute(text("SET search_path TO public"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public"))
    except Exception as postgis_error:
        logger.warning(f"⚠️ Erro ao criar extensão PostGIS (WITH SCHEMA public): {postgis_error}")

    # 3) Valida em uma nova transação limpa
    try:
        with engine.begin() as conn:
            geography_exists = conn.execute(text(
                """
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public' AND t.typname = 'geography'
                """
            )).scalar()

        if geography_exists:
            logger.info("✅ PostGIS disponível (tipo 'geography' encontrado)")
        else:
            logger.error("❌ PostGIS não disponível (tipo 'geography' ausente). Instale/habilite PostGIS no banco.")
            raise RuntimeError("PostGIS ausente: não é possível criar tabelas com colunas Geography")
    except RuntimeError:
        raise
    except Exception as e:
        # Propaga erro para interromper inicialização e evitar tabelas órfãs
        logger.error(f"❌ Erro ao validar PostGIS: {e}")
        raise


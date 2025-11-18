"""Configuração de timezone do banco de dados."""
import logging
from sqlalchemy import text
from ..db_connection import engine

logger = logging.getLogger(__name__)


def configurar_timezone():
    """Configura o timezone do banco de dados para America/Sao_Paulo."""
    try:
        with engine.begin() as conn:
            # Configura timezone da sessão
            conn.execute(text("SET timezone = 'America/Sao_Paulo'"))
            # Verifica se o timezone foi configurado corretamente
            result = conn.execute(text("SHOW timezone"))
            timezone_atual = result.scalar()
            logger.info(f"✅ Timezone do banco configurado: {timezone_atual}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao configurar timezone do banco: {e}")


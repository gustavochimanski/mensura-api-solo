# app/database/db_connection.py

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from ..config.settings import DB_CONFIG, DB_SSL_MODE
from app.core.rls_context import get_rls_empresa_id, get_rls_user_id

# Base única para todos os models
Base = declarative_base()

# Logger básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validação mínima de config
missing = [k for k in ('database', 'user', 'password', 'host', 'port') if not DB_CONFIG.get(k)]
if missing:
    raise RuntimeError(f"Configuração do banco inválida, faltando variáveis: {', '.join(missing)}")

# Monta a URL de conexão (com SSL opcional via query)
ssl_query = f"?sslmode={DB_SSL_MODE}" if DB_SSL_MODE else ""
connection_string = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}{ssl_query}"
)

# Cria o engine com configuração de timezone
engine = create_engine(
    connection_string,
    pool_pre_ping=True,
    connect_args={
        "options": "-c timezone=America/Sao_Paulo"
    }
)

# Configura o sessionmaker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Função para uso legado
def conectar():
    try:
        session = SessionLocal()
        logger.info("Sessão ORM aberta com sucesso!")
        return session
    except Exception as e:
        logger.error(f"Erro ao abrir sessão ORM: {e}")
        return None

# Dependency para FastAPI
def get_db():
    db = SessionLocal()
    try:
        # RLS (Postgres): injeta contexto do request na sessão atual.
        # Isso habilita políticas como:
        #   empresa_id = current_setting('app.empresa_id')::int
        # sem precisar criar um usuário de banco por usuário da aplicação.
        user_id = get_rls_user_id()
        empresa_id = get_rls_empresa_id()
        try:
            db.execute(
                text("SELECT set_config('app.user_id', :v, true)"),
                {"v": str(user_id) if user_id is not None else ""},
            )
            db.execute(
                text("SELECT set_config('app.empresa_id', :v, true)"),
                {"v": str(empresa_id) if empresa_id is not None else ""},
            )
        except Exception as e:
            # Não deve bloquear a API caso o banco não aceite set_config por algum motivo.
            logger.warning("Falha ao aplicar contexto RLS (set_config): %s", e)

        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

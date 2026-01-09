# app/database/db_connection.py

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..config.settings import DB_CONFIG, DB_SSL_MODE

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
        yield db
    finally:
        db.close()

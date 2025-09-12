import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega o .env manualmente se estiver fora do Docker
if not os.getenv("RUNNING_IN_DOCKER"):
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=dotenv_path)

GEOAPIFY_KEY = os.getenv("GEOAPIFY_KEY")

# Configuração de conexão
DB_CONFIG = {
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
}

# SSL do banco (opcional)
DB_SSL_MODE = os.getenv('DB_SSL_MODE')  # ex.: require, verify-ca, verify-full

# JWT / Segurança
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 90))

# CORS
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# FastAPI / App
BASE_URL = os.getenv("BASE_URL", "")
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() in ("1", "true", "yes")
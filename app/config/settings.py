import os
from dotenv import load_dotenv
from pathlib import Path

# Carrega o .env manualmente se estiver fora do Docker
if not os.getenv("RUNNING_IN_DOCKER"):
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=dotenv_path)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

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
CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() in ("1", "true", "yes")

# FastAPI / App
BASE_URL = os.getenv("BASE_URL", "")
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() in ("1", "true", "yes")

# Mercado Pago
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_BASE_URL = os.getenv("MERCADOPAGO_BASE_URL", "https://api.mercadopago.com")
MERCADOPAGO_TIMEOUT_SECONDS = int(os.getenv("MERCADOPAGO_TIMEOUT_SECONDS", 20))

# Ngrok
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-default")
STATE_CADASTRO_NOME = os.getenv("STATE_CADASTRO_NOME", "cadastro_nome")

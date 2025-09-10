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

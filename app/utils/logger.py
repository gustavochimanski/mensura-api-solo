# app/utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

# Caminho da pasta logs/
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Instância do logger
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

# Evita duplicar handlers se importar várias vezes
if not logger.handlers:
    # Formatação
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

    # Handler para arquivo com rotação
    file_handler = RotatingFileHandler(
        filename=LOG_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler opcional para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

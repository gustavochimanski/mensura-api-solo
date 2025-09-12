import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.admin_dependencies import get_current_user
from app.utils.logger import logger  # ✅ Logger centralizado
from app.config.settings import CORS_ORIGINS, CORS_ALLOW_ALL, BASE_URL as SETTINGS_BASE_URL, ENABLE_DOCS
from app.api.BI.router.router import router as bi_router
from app.api.mensura.router.router import router as mensura_router
from app.api.delivery.router.router import api_delivery
from app.api.public.router import router as public_router
from app.api.auth import auth_controller

# ───────────────────────────
# Diretórios
# ───────────────────────────
BASE_DIR = Path(__file__).resolve().parent
STATIC_IMG_DIR = BASE_DIR / "static" / "img"
STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = SETTINGS_BASE_URL or os.getenv("BASE_URL", "https://teste2.mensuraapi.com.br")
# ───────────────────────────
# Instância FastAPI
# ───────────────────────────
app = FastAPI(
    title="API de Varejo",
    version="1.0.0",
    description="Endpoints de relatórios, metas, dashboard e compras",
    docs_url=("/swagger" if ENABLE_DOCS else None),
    redoc_url=("/redoc" if ENABLE_DOCS else None),
    openapi_url=("/openapi.json" if ENABLE_DOCS else None),
    servers=[{"url": BASE_URL, "description": "Base URL do ambiente"}]
)

# ───────────────────────────
# Middlewares
# ───────────────────────────
# CORS
# ───────────────────────────
# Regra:
# - Se CORS_ALLOW_ALL=true => allow_origins=["*"], allow_credentials=False
# - Caso contrário => allow_origins=CORS_ORIGINS (se vazio cai para ["*"]), allow_credentials=True somente quando houver origens explícitas
if CORS_ALLOW_ALL:
    allowed_origins = ["*"]
    allow_credentials = False
else:
    allowed_origins = CORS_ORIGINS or ["*"]
    allow_credentials = bool(CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────────────────
# Arquivos estáticos
# ───────────────────────────
app.mount("/img", StaticFiles(directory=str(STATIC_IMG_DIR)), name="img")

# ───────────────────────────
# Startup
# ───────────────────────────
@app.on_event("startup")
def startup():
    from app.database.init_db import inicializar_banco
    logger.info("Iniciando API e banco de dados...")
    inicializar_banco()
    logger.info("API iniciada com sucesso.")

# ───────────────────────────
# Rotas
# ───────────────────────────
app.include_router(auth_controller.router)
app.include_router(api_delivery)
app.include_router(mensura_router)
app.include_router(bi_router, dependencies=[Depends(get_current_user)])
app.include_router(public_router,  dependencies=[Depends(get_current_user)])

import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.admin_dependencies import get_current_user
from app.utils.logger import logger  # ✅ Logger centralizado
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

BASE_URL = os.getenv("BASE_URL", "https://teste2.mensuraapi.com.br")
# ───────────────────────────
# Instância FastAPI
# ───────────────────────────
app = FastAPI(
    title="API de Varejo",
    version="1.0.0",
    description="Endpoints de relatórios, metas, dashboard e compras",
    docs_url="/swagger",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[{"url": BASE_URL, "description": "Base URL do ambiente"}]
)

# ───────────────────────────
# Middlewares
# ───────────────────────────]
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
    logger.info("🔥 Iniciando API e banco de dados...")
    logger.info("TESTANDO DOKCEREEEEEEEEEEEE")
    inicializar_banco()
    logger.info("✅ API iniciada com sucesso.")

# ───────────────────────────
# Rotas
# ───────────────────────────
app.include_router(auth_controller.router)
app.include_router(api_delivery)
app.include_router(mensura_router, dependencies=[Depends(get_current_user)])
app.include_router(bi_router, dependencies=[Depends(get_current_user)])
app.include_router(public_router,  dependencies=[Depends(get_current_user)])

import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

from app.core.admin_dependencies import get_current_user
from app.core.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from app.utils.logger import logger 
from app.config.settings import CORS_ORIGINS, CORS_ALLOW_ALL, BASE_URL as SETTINGS_BASE_URL, ENABLE_DOCS

# ───────────────────────────
# Importar modelos antes das rotas
# Garante que todos os modelos estejam registrados no SQLAlchemy
# antes de qualquer query ser executada
# ───────────────────────────

from app.api.auth import auth_controller
from app.api.cardapio.router.router import api_cardapio
from app.api.cadastros.router.router import api_cadastros
from app.api.cadastros.router.admin.router_mesas import router as router_mesas
from app.api.empresas.router.router import api_empresas
from app.api.pedidos.router.router import api_pedidos
from app.api.relatorios.router.router import router as relatorios_router
from app.api.notifications.router.router import router as notifications_router
from app.api.caixas.router.router import router as caixa_router
from app.api.localizacao.router.router_localizacao import router as localizacao_router
from app.api.catalogo.router.router import router as catalogo_router
from app.api.chatbot.router.router import router as chatbot_router


# ───────────────────────────
# Diretórios
# ──────────────────────────-
BASE_DIR = Path(__file__).resolve().parent
STATIC_IMG_DIR = BASE_DIR / "static" / "img"
STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = SETTINGS_BASE_URL or os.getenv("BASE_URL", "https://teste2.mensuraapi.com.br")
# ──────────────────────────
# Instância FastAPI
# ──────────────────────────
app = FastAPI(
    title="API de Varejo",
    version="1.0.0",
    description="Endpoints de relatórios, metas, dashboard e compras",
    docs_url=("/swagger" if ENABLE_DOCS else None),
    redoc_url=("/redoc" if ENABLE_DOCS else None),

    openapi_url=("/openapi.json" if ENABLE_DOCS else None),
    servers=[{"url": BASE_URL, "description": "Base URL do ambiente"}],
    redirect_slashes=False  # Evita redirecionamento 307 quando URL não termina com /
)

# ───────────────────────────
# Exception Handlers Globais
# ───────────────────────────
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# ───────────────────────────
# Middlewares
# ───────────────────────────
# IMPORTANTE: A ordem dos middlewares importa!
# Middlewares são executados na ORDEM REVERSA da adição (último adicionado = primeiro executado)
# ───────────────────────────

# Prometheus Middleware (para coletar métricas)
from app.utils.prometheus_metrics import PrometheusMiddleware
app.add_middleware(PrometheusMiddleware)


# CORS (adicionado por último, será executado primeiro)
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
async def startup():
    from app.database.init_db import inicializar_banco
    from app.database.db_connection import get_db
    from app.api.notifications.core.notification_system import initialize_notification_system
    from app.api.chatbot.core import database as chatbot_db

    logger.info("Iniciando API e banco de dados...")
    inicializar_banco()

    # Inicializa sistema de notificações
    try:
        db = next(get_db())
        await initialize_notification_system(db)
        logger.info("Sistema de notificações inicializado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de notificações: {e}")

    # Inicializa banco de dados do chatbot
    try:
        db = next(get_db())
        chatbot_db.init_database(db)
        chatbot_db.seed_default_prompts(db)
        logger.info("Sistema de chatbot inicializado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de chatbot: {e}")

    logger.info("API iniciada com sucesso.")

# ───────────────────────────
# Shutdown
# ───────────────────────────
@app.on_event("shutdown")
async def shutdown():
    from app.api.notifications.core.notification_system import shutdown_notification_system
    
    logger.info("Encerrando API...")
    
    # Encerra sistema de notificações
    try:
        await shutdown_notification_system()
        logger.info("Sistema de notificações encerrado com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao encerrar sistema de notificações: {e}")
    
    logger.info("API encerrada.")

# ───────────────────────────
# Rotas
# ───────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# ───────────────────────────
# Monitoring - Monitoramento e Métricas
# ───────────────────────────
from app.api.monitoring.router import router as monitoring_router, router_public as monitoring_router_public
app.include_router(monitoring_router_public)  # Métricas públicas (sem auth)
app.include_router(monitoring_router)  # Logs com autenticação
#
# ───────────────────────────
# Routers
# ───────────────────────────
app.include_router(auth_controller.router)
app.include_router(api_cardapio)
app.include_router(api_cadastros)
app.include_router(router_mesas)  # Router de mesas em /api/mesas/admin/mesas
app.include_router(api_empresas)
app.include_router(api_pedidos)
app.include_router(relatorios_router)
app.include_router(notifications_router)
app.include_router(caixa_router)
app.include_router(localizacao_router)
app.include_router(catalogo_router)
app.include_router(chatbot_router)

# ───────────────────────────
# OpenAPI: Segurança Bearer/JWT no Swagger
# ───────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
    )

    components = openapi_schema.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    security_schemes.update({
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    })
    components["securitySchemes"] = security_schemes
    openapi_schema["components"] = components

    # Define segurança global
    openapi_schema["security"] = [{"bearerAuth": []}]

    # Remover exigência de token de endpoints públicos
    public_paths = {"/", "/health", "/api/auth/token"}
    paths = openapi_schema.get("paths", {})
    for path, methods in paths.items():
        if path in public_paths:
            for method_obj in methods.values():
                # Overwrite para remover security no nível da operação
                method_obj["security"] = []

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ───────────────────────────
# Swagger UI Separado para cada API
# ───────────────────────────

def get_filtered_openapi(tag_filter: str, path_prefix: str, title: str):
    """Gera OpenAPI schema filtrado por tag ou prefixo de path"""
    if not ENABLE_DOCS:
        return {}
    
    # Primeiro, gera o OpenAPI completo
    full_openapi = get_openapi(
        title=title,
        version=app.version,
        description=f"Documentação da API {title}",
        routes=app.routes,
        servers=app.servers,
    )
    
    # Filtra paths que pertencem à API (por tag ou prefixo)
    paths = full_openapi.get("paths", {})
    filtered_paths = {}
    all_tags = set()  # Coleta todas as tags dos endpoints filtrados
    
    for path, methods in paths.items():
        filtered_methods = {}
        for method, details in methods.items():
            if isinstance(details, dict):
                tags = details.get("tags", [])
                # Verifica se a tag está na lista OU se o path começa com o prefixo
                should_include = False
                
                # Filtro por tag principal (ex: "API - Delivery")
                if tag_filter in tags:
                    should_include = True
                # Filtro por prefixo de path (para pegar todos os sub-routers)
                elif path.startswith(path_prefix):
                    should_include = True
                # Para auth, verificar se tem a tag "auth"
                elif tag_filter == "auth" and "auth" in tags:
                    should_include = True
                
                if should_include:
                    filtered_methods[method] = details
                    # Coleta todas as tags deste endpoint
                    if tags:
                        all_tags.update(tags)
        if filtered_methods:
            filtered_paths[path] = filtered_methods
    
    # Atualiza o schema com paths filtrados
    full_openapi["paths"] = filtered_paths
    
    # Remove tags que não pertencem aos endpoints filtrados
    # E cria lista de tags no formato OpenAPI, preservando ordem alfabética
    original_tags = full_openapi.get("tags", [])
    tags_dict = {tag.get("name"): tag for tag in original_tags if isinstance(tag, dict)}
    
    # Cria nova lista de tags apenas com as que estão nos endpoints filtrados
    tags_list = []
    for tag_name in sorted(all_tags):
        if tag_name in tags_dict:
            # Preserva informações extras da tag original (como description)
            tags_list.append(tags_dict[tag_name])
        else:
            # Cria entrada básica se não existir na lista original
            tags_list.append({"name": tag_name})
    
    full_openapi["tags"] = tags_list
    
    # Filtra também os componentes que não são usados
    if filtered_paths:
        # Mantém todos os schemas pois podem ser referenciados
        pass
    else:
        # Se não há paths, limpa components
        full_openapi["components"] = {}
    
    # Adiciona segurança se ainda não existir
    components = full_openapi.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    if "bearerAuth" not in security_schemes:
        security_schemes.update({
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        })
        components["securitySchemes"] = security_schemes
        full_openapi["components"] = components
    
    # Define segurança global
    full_openapi["security"] = [{"bearerAuth": []}]
    
    # Remove security de endpoints públicos
    public_paths = {"/", "/health", "/api/auth/token"}
    for path in public_paths:
        if path in filtered_paths:
            for method_obj in filtered_paths[path].values():
                if isinstance(method_obj, dict):
                    method_obj["security"] = []
    
    return full_openapi

@app.get("/swagger/auth", include_in_schema=False)
async def swagger_auth():
    """Swagger UI para API de Autenticação"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/auth.json",
        title="API de Autenticação - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/auth.json", include_in_schema=False)
async def openapi_auth():
    """OpenAPI schema para API de Autenticação"""
    return get_filtered_openapi("auth", "/api/auth", "API de Autenticação")

@app.get("/swagger/cardapio", include_in_schema=False)
async def swagger_cardapio():
    """Swagger UI para API de Cardápio"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/cardapio.json",
        title="API de Cardápio - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/cardapio.json", include_in_schema=False)
async def openapi_cardapio():
    """OpenAPI schema para API de Cardápio"""
    return get_filtered_openapi("API - Cardápio", "/api/cardapio", "API de Cardápio")

@app.get("/swagger/mensura", include_in_schema=False)
async def swagger_mensura():
    """Swagger UI para API de Mensura"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/mensura.json",
        title="API de Mensura - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/mensura.json", include_in_schema=False)
async def openapi_mensura():
    """OpenAPI schema para API de Mensura"""
    return get_filtered_openapi("API - Mensura", "/api/mensura", "API de Mensura")

@app.get("/swagger/mesas", include_in_schema=False)
async def swagger_mesas():
    """Swagger UI para API de Mesas"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/mesas.json",
        title="API de Mesas - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/mesas.json", include_in_schema=False)
async def openapi_mesas():
    """OpenAPI schema para API de Mesas"""
    return get_filtered_openapi("API - Mesas", "/api/mesas", "API de Mesas")

@app.get("/swagger/relatorios", include_in_schema=False)
async def swagger_relatorios():
    """Swagger UI para API de Relatórios"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/relatorios.json",
        title="API de Relatórios - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/relatorios.json", include_in_schema=False)
async def openapi_relatorios():
    """OpenAPI schema para API de Relatórios"""
    return get_filtered_openapi("API - Relatórios", "/api/relatorios", "API de Relatórios")

@app.get("/swagger/notifications", include_in_schema=False)
async def swagger_notifications():
    """Swagger UI para API de Notificações"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/notifications.json",
        title="API de Notificações - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/notifications.json", include_in_schema=False)
async def openapi_notifications():
    """OpenAPI schema para API de Notificações"""
    return get_filtered_openapi("API - Notifications", "/api/notifications", "API de Notificações")

@app.get("/swagger/caixa", include_in_schema=False)
async def swagger_caixa():
    """Swagger UI para API de Caixa"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/caixa.json",
        title="API de Caixa - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/caixa.json", include_in_schema=False)
async def openapi_caixa():
    """OpenAPI schema para API de Caixa"""
    return get_filtered_openapi("API - Caixa", "/api/caixa", "API de Caixa")

@app.get("/swagger/cadastros", include_in_schema=False)
async def swagger_cadastros():
    """Swagger UI para API de Cadastros"""
    if not ENABLE_DOCS:
        return {"message": "Documentação desabilitada"}
    return get_swagger_ui_html(
        openapi_url="/openapi/cadastros.json",
        title="API de Cadastros - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "filter": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha"
        }
    )

@app.get("/openapi/cadastros.json", include_in_schema=False)
async def openapi_cadastros():
    """OpenAPI schema para API de Cadastros"""
    return get_filtered_openapi("API - Cadastros", "/api/cadastros", "API de Cadastros")

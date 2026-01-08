from fastapi import APIRouter
from .websocket_router import router as websocket_router
from .historico_router import router as historico_router
from .message_dispatch_router import router as message_dispatch_router
from .whatsapp_config_router import router as whatsapp_config_router

# Router principal que agrupa todos os endpoints de notificações
router = APIRouter(
    prefix="/api/notifications",
    tags=["API - Notifications"]
)

# Inclui apenas os routers utilizados:
# - websocket_router: WebSocket principal + rotas de estatísticas
# - historico_router: Rotas de consulta/estatísticas (admin)
# - message_dispatch_router: Disparo de mensagens (usado pelo frontend)
router.include_router(websocket_router)
router.include_router(historico_router)
router.include_router(message_dispatch_router)
router.include_router(whatsapp_config_router)

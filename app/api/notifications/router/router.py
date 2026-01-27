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

# Rotas ADMIN (histórico e configurações)
admin_router = APIRouter(prefix="/admin", tags=["API - Notifications (Admin)"])
admin_router.include_router(historico_router)

# Rotas públicas/autenticadas
router.include_router(websocket_router)
router.include_router(message_dispatch_router)
router.include_router(admin_router)
# WhatsApp configs em /api/notifications/whatsapp-configs (conforme documentação)
router.include_router(whatsapp_config_router)

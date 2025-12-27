from fastapi import APIRouter
from .notification_router import router as notification_router
from .subscription_router import router as subscription_router
from .event_router import router as event_router
from .websocket_router import router as websocket_router
from .pedido_router import router as pedido_router
from .historico_router import router as historico_router
from .message_dispatch_router import router as message_dispatch_router

# Router principal que agrupa todos os endpoints de notificações
router = APIRouter(
    prefix="/api/notifications",
    tags=["API - Notifications"]
)

# Inclui todos os sub-routers
router.include_router(notification_router)
router.include_router(subscription_router)
router.include_router(event_router)
router.include_router(websocket_router)
router.include_router(pedido_router)
router.include_router(historico_router)
router.include_router(message_dispatch_router)

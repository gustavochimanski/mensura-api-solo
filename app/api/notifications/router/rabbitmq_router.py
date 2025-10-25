from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..services.rabbitmq_notification_service import RabbitMQNotificationService
from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rabbitmq", tags=["rabbitmq"])

def get_rabbitmq_service(db: Session = Depends(get_db)) -> RabbitMQNotificationService:
    """Dependency para obter o serviço RabbitMQ"""
    notification_repo = NotificationRepository(db)
    subscription_repo = SubscriptionRepository(db)
    event_repo = EventRepository(db)
    return RabbitMQNotificationService(notification_repo, subscription_repo, event_repo)

@router.get("/status")
async def get_rabbitmq_status(
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Retorna status do RabbitMQ"""
    try:
        stats = await service.get_rabbitmq_stats()
        return {
            "status": "connected" if stats.get("connected") else "disconnected",
            "info": stats
        }
    except Exception as e:
        logger.error(f"Erro ao buscar status do RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-notification")
async def send_notification_rabbitmq(
    empresa_id: str,
    user_id: Optional[str],
    event_type: str,
    title: str,
    message: str,
    channel: str,
    recipient: str,
    priority: str = "normal",
    channel_metadata: Optional[Dict[str, Any]] = None,
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Envia notificação via RabbitMQ"""
    try:
        notification_id = await service.send_notification(
            empresa_id=empresa_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            channel=channel,
            recipient=recipient,
            priority=priority,
            channel_metadata=channel_metadata
        )
        
        if notification_id:
            return {
                "success": True,
                "message": "Notificação enviada via RabbitMQ",
                "notification_id": notification_id
            }
        else:
            raise HTTPException(status_code=500, detail="Falha ao enviar notificação")
            
    except Exception as e:
        logger.error(f"Erro ao enviar notificação via RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-bulk-notifications")
async def send_bulk_notifications_rabbitmq(
    empresa_id: str,
    event_type: str,
    title: str,
    message: str,
    channels: List[str],
    recipients: Dict[str, str],
    priority: str = "normal",
    channel_metadata: Optional[Dict[str, Any]] = None,
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Envia notificações em lote via RabbitMQ"""
    try:
        notification_ids = await service.send_bulk_notifications(
            empresa_id=empresa_id,
            event_type=event_type,
            title=title,
            message=message,
            channels=channels,
            recipients=recipients,
            priority=priority,
            channel_metadata=channel_metadata
        )
        
        return {
            "success": True,
            "message": f"Notificações enviadas via RabbitMQ",
            "notification_ids": notification_ids,
            "total_sent": len(notification_ids)
        }
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificações em lote via RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notification/{notification_id}/status")
async def get_notification_status(
    notification_id: str,
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Busca status de uma notificação"""
    try:
        status = await service.get_notification_status(notification_id)
        
        if status:
            return {
                "success": True,
                "notification": status
            }
        else:
            raise HTTPException(status_code=404, detail="Notificação não encontrada")
            
    except Exception as e:
        logger.error(f"Erro ao buscar status da notificação {notification_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry-failed")
async def retry_failed_notifications(
    limit: int = Query(50, ge=1, le=100, description="Limite de notificações para reprocessar"),
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Tenta reenviar notificações que falharam via RabbitMQ"""
    try:
        retried_count = await service.retry_failed_notifications(limit)
        
        return {
            "success": True,
            "message": f"Tentativa de reenvio de {retried_count} notificações falhadas",
            "retried_count": retried_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao reenviar notificações falhadas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queues")
async def get_rabbitmq_queues(
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Lista queues do RabbitMQ"""
    try:
        stats = await service.get_rabbitmq_stats()
        
        return {
            "queues": stats.get("queues", []),
            "exchanges": stats.get("exchanges", []),
            "connection_info": {
                "host": stats.get("host"),
                "port": stats.get("port"),
                "virtual_host": stats.get("virtual_host"),
                "connected": stats.get("connected")
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar queues do RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-connection")
async def test_rabbitmq_connection(
    service: RabbitMQNotificationService = Depends(get_rabbitmq_service),
    current_user = Depends(get_current_user)
):
    """Testa conexão com RabbitMQ"""
    try:
        # Tenta enviar uma notificação de teste
        test_notification_id = await service.send_notification(
            empresa_id="test",
            user_id="test",
            event_type="test",
            title="Teste de Conexão",
            message="Esta é uma notificação de teste",
            channel="in_app",
            recipient="test",
            channel_metadata={"test": True}
        )
        
        if test_notification_id:
            return {
                "success": True,
                "message": "Conexão com RabbitMQ funcionando",
                "test_notification_id": test_notification_id
            }
        else:
            raise HTTPException(status_code=500, detail="Falha no teste de conexão")
            
    except Exception as e:
        logger.error(f"Erro no teste de conexão RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

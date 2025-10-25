from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..services.notification_service import NotificationService
from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.event_repository import EventRepository
from ..schemas.notification_schemas import (
    CreateNotificationRequest,
    SendNotificationRequest,
    NotificationResponse,
    NotificationListResponse,
    NotificationFilter,
    NotificationLogResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])

def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    """Dependency para obter o serviço de notificações"""
    notification_repo = NotificationRepository(db)
    subscription_repo = SubscriptionRepository(db)
    event_repo = EventRepository(db)
    return NotificationService(notification_repo, subscription_repo, event_repo)

@router.post("/", response_model=NotificationResponse)
async def create_notification(
    request: CreateNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Cria uma nova notificação"""
    try:
        notification_id = await service.create_notification(request)
        notification = service.get_notification_by_id(notification_id)
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notificação não encontrada")
        
        return NotificationResponse.from_orm(notification)
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send", response_model=List[str])
async def send_notification(
    request: SendNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Envia notificação para múltiplos canais"""
    try:
        notification_ids = await service.send_notification(request)
        return notification_ids
    except Exception as e:
        logger.error(f"Erro ao enviar notificação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Busca notificação por ID"""
    notification = service.get_notification_by_id(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    return NotificationResponse.from_orm(notification)

@router.get("/{notification_id}/logs", response_model=List[NotificationLogResponse])
async def get_notification_logs(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Busca logs de uma notificação"""
    logs = service.get_notification_logs(notification_id)
    return [NotificationLogResponse.from_orm(log) for log in logs]

@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    empresa_id: Optional[str] = Query(None, description="ID da empresa"),
    user_id: Optional[str] = Query(None, description="ID do usuário"),
    event_type: Optional[str] = Query(None, description="Tipo do evento"),
    channel: Optional[str] = Query(None, description="Canal de notificação"),
    status: Optional[str] = Query(None, description="Status da notificação"),
    priority: Optional[str] = Query(None, description="Prioridade"),
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(50, ge=1, le=100, description="Itens por página"),
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Lista notificações com filtros"""
    try:
        filters = NotificationFilter(
            empresa_id=empresa_id,
            user_id=user_id,
            event_type=event_type,
            channel=channel,
            status=status,
            priority=priority
        )
        
        offset = (page - 1) * per_page
        notifications = service.notification_repo.filter_notifications(filters, per_page, offset)
        total = service.notification_repo.count_notifications(filters)
        
        notification_responses = [NotificationResponse.from_orm(n) for n in notifications]
        
        return NotificationListResponse(
            notifications=notification_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        logger.error(f"Erro ao listar notificações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-pending")
async def process_pending_notifications(
    background_tasks: BackgroundTasks,
    limit: int = Query(50, ge=1, le=100, description="Limite de notificações para processar"),
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Processa notificações pendentes em background"""
    try:
        background_tasks.add_task(service.process_pending_notifications, limit)
        return {"message": f"Processamento de {limit} notificações pendentes iniciado"}
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento de notificações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry-failed")
async def retry_failed_notifications(
    background_tasks: BackgroundTasks,
    limit: int = Query(50, ge=1, le=100, description="Limite de notificações para reprocessar"),
    service: NotificationService = Depends(get_notification_service),
    current_user = Depends(get_current_user)
):
    """Tenta reenviar notificações que falharam"""
    try:
        background_tasks.add_task(service.retry_failed_notifications, limit)
        return {"message": f"Tentativa de reenvio de {limit} notificações falhadas iniciada"}
    except Exception as e:
        logger.error(f"Erro ao iniciar reenvio de notificações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

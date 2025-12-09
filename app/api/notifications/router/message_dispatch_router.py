from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..services.message_dispatch_service import MessageDispatchService
from ..services.notification_service import NotificationService
from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.event_repository import EventRepository
from ..schemas.message_dispatch_schemas import (
    DispatchMessageRequest,
    DispatchMessageResponse,
    BulkDispatchRequest
)
from ..models.notification import MessageType
from ..adapters.recipient_adapters import ClienteRecipientAdapter, CompositeRecipientAdapter
from ..adapters.channel_config_adapters import DefaultChannelConfigAdapter, CompositeChannelConfigAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["message-dispatch"])

def get_message_dispatch_service(db: Session = Depends(get_db)) -> MessageDispatchService:
    """Dependency para obter o serviço de disparo de mensagens"""
    notification_repo = NotificationRepository(db)
    subscription_repo = SubscriptionRepository(db)
    event_repo = EventRepository(db)
    
    # Configura provedor de configuração de canais
    channel_config_provider = DefaultChannelConfigAdapter()
    
    # Cria serviço de notificações com provedor de configuração
    notification_service = NotificationService(
        notification_repo,
        subscription_repo,
        event_repo,
        channel_config_provider=channel_config_provider
    )
    
    # Configura provedor de destinatários
    cliente_adapter = ClienteRecipientAdapter(db)
    recipient_provider = CompositeRecipientAdapter([cliente_adapter])
    
    # Cria serviço de disparo com provedor de destinatários
    return MessageDispatchService(
        notification_service,
        db=db,
        recipient_provider=recipient_provider
    )

@router.post("/dispatch", response_model=DispatchMessageResponse)
async def dispatch_message(
    request: DispatchMessageRequest,
    service: MessageDispatchService = Depends(get_message_dispatch_service),
    current_user = Depends(get_current_user)
):
    """
    Dispara uma mensagem para um ou mais destinatários através de múltiplos canais.
    
    O tipo da mensagem (marketing, utility, transactional, etc) deve ser especificado
    para controle e classificação adequada.
    """
    try:
        response = await service.dispatch_message(request)
        return response
    except ValueError as e:
        logger.error(f"Erro de validação ao disparar mensagem: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao disparar mensagem: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao disparar mensagem: {str(e)}")

@router.post("/bulk-dispatch", response_model=DispatchMessageResponse)
async def bulk_dispatch_message(
    request: BulkDispatchRequest,
    service: MessageDispatchService = Depends(get_message_dispatch_service),
    current_user = Depends(get_current_user)
):
    """
    Dispara mensagem em massa baseado em filtros.
    
    Útil para campanhas de marketing ou notificações para grupos de usuários.
    """
    try:
        response = await service.bulk_dispatch(request)
        return response
    except ValueError as e:
        logger.error(f"Erro de validação no disparo em massa: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro no disparo em massa: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no disparo em massa: {str(e)}")

@router.get("/stats")
async def get_dispatch_stats(
    empresa_id: str = Query(..., description="ID da empresa"),
    message_type: Optional[MessageType] = Query(None, description="Filtrar por tipo de mensagem"),
    start_date: Optional[datetime] = Query(None, description="Data inicial"),
    end_date: Optional[datetime] = Query(None, description="Data final"),
    service: MessageDispatchService = Depends(get_message_dispatch_service),
    current_user = Depends(get_current_user)
):
    """
    Obtém estatísticas de disparos de mensagens.
    
    Permite filtrar por tipo de mensagem e período.
    """
    try:
        stats = service.get_dispatch_stats(
            empresa_id=empresa_id,
            message_type=message_type,
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


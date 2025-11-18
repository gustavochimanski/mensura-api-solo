from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..services.subscription_service import SubscriptionService
from ..repositories.subscription_repository import SubscriptionRepository
from ..schemas.subscription_schemas import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionFilter
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

def get_subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    """Dependency para obter o serviço de assinaturas"""
    subscription_repo = SubscriptionRepository(db)
    return SubscriptionService(subscription_repo)

@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Cria uma nova assinatura de notificação"""
    try:
        subscription_id = service.create_subscription(request)
        subscription = service.get_subscription_by_id(subscription_id)
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        return SubscriptionResponse.from_orm(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao criar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Busca assinatura por ID"""
    subscription = service.get_subscription_by_id(subscription_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    return SubscriptionResponse.from_orm(subscription)

@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    request: UpdateSubscriptionRequest,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Atualiza uma assinatura"""
    try:
        success = service.update_subscription(subscription_id, request)
        
        if not success:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        subscription = service.get_subscription_by_id(subscription_id)
        return SubscriptionResponse.from_orm(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao atualizar assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Remove uma assinatura"""
    try:
        success = service.delete_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        return {"message": "Assinatura removida com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao remover assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{subscription_id}/toggle")
async def toggle_subscription(
    subscription_id: str,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Ativa/desativa uma assinatura"""
    try:
        success = service.toggle_subscription(subscription_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        subscription = service.get_subscription_by_id(subscription_id)
        status = "ativada" if subscription.active else "desativada"
        
        return {"message": f"Assinatura {status} com sucesso", "active": subscription.active}
    except Exception as e:
        logger.error(f"Erro ao alterar status da assinatura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=SubscriptionListResponse)
async def list_subscriptions(
    empresa_id: Optional[str] = Query(None, description="ID da empresa"),
    user_id: Optional[str] = Query(None, description="ID do usuário"),
    event_type: Optional[str] = Query(None, description="Tipo do evento"),
    channel: Optional[str] = Query(None, description="Canal de notificação"),
    active: Optional[bool] = Query(None, description="Status ativo"),
    page: int = Query(1, ge=1, description="Página"),
    per_page: int = Query(50, ge=1, le=100, description="Itens por página"),
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Lista assinaturas com filtros"""
    try:
        filters = SubscriptionFilter(
            empresa_id=empresa_id,
            user_id=user_id,
            event_type=event_type,
            channel=channel,
            active=active
        )
        
        offset = (page - 1) * per_page
        subscriptions = service.filter_subscriptions(filters, per_page, offset)
        total = service.count_subscriptions(filters)
        
        subscription_responses = [SubscriptionResponse.from_orm(s) for s in subscriptions]
        
        return SubscriptionListResponse(
            subscriptions=subscription_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        logger.error(f"Erro ao listar assinaturas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/empresa/{empresa_id}", response_model=List[SubscriptionResponse])
async def get_empresa_subscriptions(
    empresa_id: str,
    limit: int = Query(100, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset"),
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Busca assinaturas de uma empresa"""
    try:
        subscriptions = service.get_subscriptions_by_empresa(empresa_id, limit, offset)
        return [SubscriptionResponse.from_orm(s) for s in subscriptions]
    except Exception as e:
        logger.error(f"Erro ao buscar assinaturas da empresa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    user_id: str,
    limit: int = Query(100, ge=1, le=500, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset"),
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Busca assinaturas de um usuário"""
    try:
        subscriptions = service.get_user_subscriptions(user_id, limit, offset)
        return [SubscriptionResponse.from_orm(s) for s in subscriptions]
    except Exception as e:
        logger.error(f"Erro ao buscar assinaturas do usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/channels/supported")
async def get_supported_channels(
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Retorna lista de canais suportados"""
    try:
        channels = service.get_supported_channels()
        return {"channels": channels}
    except Exception as e:
        logger.error(f"Erro ao buscar canais suportados: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/channels/test")
async def test_channel_config(
    channel: str,
    config: dict,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Testa configuração de um canal"""
    try:
        result = service.test_channel_config(channel, config)
        return result
    except Exception as e:
        logger.error(f"Erro ao testar canal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics/{empresa_id}")
async def get_subscription_statistics(
    empresa_id: str,
    service: SubscriptionService = Depends(get_subscription_service),
    current_user = Depends(get_current_user)
):
    """Retorna estatísticas de assinaturas de uma empresa"""
    try:
        statistics = service.get_subscription_statistics(empresa_id)
        return statistics
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

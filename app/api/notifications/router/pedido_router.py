from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
import logging

from ....core.admin_dependencies import get_current_user
from ..services.pedido_notification_service import PedidoNotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pedidos", tags=["pedido-notifications"])

def get_pedido_notification_service() -> PedidoNotificationService:
    """Dependency para obter o serviço de notificações de pedidos"""
    return PedidoNotificationService()

@router.post("/novo-pedido")
async def notificar_novo_pedido(
    empresa_id: str,
    pedido_id: str,
    cliente_data: Dict[str, Any],
    itens: list,
    valor_total: float,
    channel_metadata: Optional[Dict[str, Any]] = None,
    service: PedidoNotificationService = Depends(get_pedido_notification_service),
    current_user = Depends(get_current_user)
):
    """
    Notifica sobre um novo pedido criado
    
    Este endpoint deve ser chamado sempre que um novo pedido for criado no sistema.
    Ele irá:
    1. Publicar um evento no sistema de eventos
    2. Enviar notificação em tempo real via WebSocket para todos os usuários da empresa
    3. Processar assinaturas de notificação configuradas
    """
    try:
        event_id = await service.notify_novo_pedido(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            cliente_data=cliente_data,
            itens=itens,
            valor_total=valor_total,
            channel_metadata=channel_metadata
        )
        
        return {
            "success": True,
            "message": "Notificação de novo pedido enviada com sucesso",
            "event_id": event_id,
            "pedido_id": pedido_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao notificar novo pedido {pedido_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pedido-aprovado")
async def notificar_pedido_aprovado(
    empresa_id: str,
    pedido_id: str,
    aprovado_por: str,
    channel_metadata: Optional[Dict[str, Any]] = None,
    service: PedidoNotificationService = Depends(get_pedido_notification_service),
    current_user = Depends(get_current_user)
):
    """Notifica sobre pedido aprovado"""
    try:
        event_id = await service.notify_pedido_aprovado(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            aprovado_por=aprovado_por,
            channel_metadata=channel_metadata
        )
        
        return {
            "success": True,
            "message": "Notificação de pedido aprovado enviada com sucesso",
            "event_id": event_id,
            "pedido_id": pedido_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao notificar pedido aprovado {pedido_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pedido-cancelado")
async def notificar_pedido_cancelado(
    empresa_id: str,
    pedido_id: str,
    motivo: str,
    cancelado_por: str,
    channel_metadata: Optional[Dict[str, Any]] = None,
    service: PedidoNotificationService = Depends(get_pedido_notification_service),
    current_user = Depends(get_current_user)
):
    """Notifica sobre pedido cancelado"""
    try:
        event_id = await service.notify_pedido_cancelado(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            motivo=motivo,
            cancelado_por=cancelado_por,
            channel_metadata=channel_metadata
        )
        
        return {
            "success": True,
            "message": "Notificação de pedido cancelado enviada com sucesso",
            "event_id": event_id,
            "pedido_id": pedido_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao notificar pedido cancelado {pedido_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pedido-entregue")
async def notificar_pedido_entregue(
    empresa_id: str,
    pedido_id: str,
    entregue_por: str,
    channel_metadata: Optional[Dict[str, Any]] = None,
    service: PedidoNotificationService = Depends(get_pedido_notification_service),
    current_user = Depends(get_current_user)
):
    """Notifica sobre pedido entregue"""
    try:
        event_id = await service.notify_pedido_entregue(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            entregue_por=entregue_por,
            channel_metadata=channel_metadata
        )
        
        return {
            "success": True,
            "message": "Notificação de pedido entregue enviada com sucesso",
            "event_id": event_id,
            "pedido_id": pedido_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao notificar pedido entregue {pedido_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

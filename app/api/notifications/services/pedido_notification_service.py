from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..core.websocket_manager import websocket_manager
from ..core.event_publisher import EventPublisher
from ..core.event_bus import event_bus

logger = logging.getLogger(__name__)

class PedidoNotificationService:
    """Serviço específico para notificações de pedidos"""
    
    def __init__(self):
        self.event_publisher = EventPublisher(event_bus)
    
    async def notify_novo_pedido(
        self,
        empresa_id: str,
        pedido_id: str,
        cliente_data: Dict[str, Any],
        itens: list,
        valor_total: float,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Notifica sobre um novo pedido criado
        
        Args:
            empresa_id: ID da empresa
            pedido_id: ID do pedido
            cliente_data: Dados do cliente
            itens: Lista de itens do pedido
            valor_total: Valor total do pedido
            metadata: Metadados adicionais
        
        Returns:
            ID do evento criado
        """
        try:
            # Publica o evento no sistema
            event_id = await self.event_publisher.publish_pedido_criado(
                empresa_id=empresa_id,
                pedido_id=pedido_id,
                cliente_data=cliente_data,
                itens=itens,
                valor_total=valor_total,
                channel_metadata=channel_metadata
            )
            
            # Envia notificação em tempo real via WebSocket
            await self._send_realtime_notification(
                empresa_id=empresa_id,
                notification_type="novo_pedido",
                title="Novo Pedido Recebido",
                message=f"Pedido #{pedido_id} criado - Valor: R$ {valor_total:.2f}",
                data={
                    "pedido_id": pedido_id,
                    "cliente": cliente_data,
                    "valor_total": valor_total,
                    "itens_count": len(itens),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Notificação de novo pedido enviada: {pedido_id} para empresa {empresa_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao notificar novo pedido {pedido_id}: {e}")
            raise
    
    async def notify_pedido_aprovado(
        self,
        empresa_id: str,
        pedido_id: str,
        aprovado_por: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Notifica sobre pedido aprovado"""
        try:
            # Publica o evento
            event_id = await self.event_publisher.publish_pedido_aprovado(
                empresa_id=empresa_id,
                pedido_id=pedido_id,
                aprovado_por=aprovado_por,
                channel_metadata=channel_metadata
            )
            
            # Envia notificação em tempo real
            await self._send_realtime_notification(
                empresa_id=empresa_id,
                notification_type="pedido_aprovado",
                title="Pedido Aprovado",
                message=f"Pedido #{pedido_id} foi aprovado por {aprovado_por}",
                data={
                    "pedido_id": pedido_id,
                    "aprovado_por": aprovado_por,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Notificação de pedido aprovado enviada: {pedido_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao notificar pedido aprovado {pedido_id}: {e}")
            raise
    
    async def notify_pedido_cancelado(
        self,
        empresa_id: str,
        pedido_id: str,
        motivo: str,
        cancelado_por: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Notifica sobre pedido cancelado"""
        try:
            # Publica o evento
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type="pedido_cancelado",
                data={
                    "pedido_id": pedido_id,
                    "motivo": motivo,
                    "cancelado_por": cancelado_por,
                    "status": "cancelado"
                },
                event_id=pedido_id,
                channel_metadata=channel_metadata
            )
            
            # Envia notificação em tempo real
            await self._send_realtime_notification(
                empresa_id=empresa_id,
                notification_type="pedido_cancelado",
                title="Pedido Cancelado",
                message=f"Pedido #{pedido_id} foi cancelado - Motivo: {motivo}",
                data={
                    "pedido_id": pedido_id,
                    "motivo": motivo,
                    "cancelado_por": cancelado_por,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Notificação de pedido cancelado enviada: {pedido_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao notificar pedido cancelado {pedido_id}: {e}")
            raise
    
    async def notify_pedido_entregue(
        self,
        empresa_id: str,
        pedido_id: str,
        entregue_por: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Notifica sobre pedido entregue"""
        try:
            # Publica o evento
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type="pedido_entregue",
                data={
                    "pedido_id": pedido_id,
                    "entregue_por": entregue_por,
                    "status": "entregue"
                },
                event_id=pedido_id,
                channel_metadata=channel_metadata
            )
            
            # Envia notificação em tempo real
            await self._send_realtime_notification(
                empresa_id=empresa_id,
                notification_type="pedido_entregue",
                title="Pedido Entregue",
                message=f"Pedido #{pedido_id} foi entregue por {entregue_por}",
                data={
                    "pedido_id": pedido_id,
                    "entregue_por": entregue_por,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Notificação de pedido entregue enviada: {pedido_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao notificar pedido entregue {pedido_id}: {e}")
            raise
    
    async def _send_realtime_notification(
        self,
        empresa_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any]
    ):
        """Envia notificação em tempo real via WebSocket"""
        try:
            notification_data = {
                "type": "notification",
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "data": data,
                "empresa_id": empresa_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Envia para todos os usuários da empresa conectados
            sent_count = await websocket_manager.send_to_empresa(empresa_id, notification_data)
            
            if sent_count > 0:
                logger.info(f"Notificação enviada para {sent_count} usuários da empresa {empresa_id}")
            else:
                logger.warning(f"Nenhum usuário conectado na empresa {empresa_id}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar notificação em tempo real: {e}")
            # Não propaga o erro para não quebrar o fluxo principal

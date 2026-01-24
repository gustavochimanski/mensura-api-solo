from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..core.websocket_manager import websocket_manager
from ..core.ws_events import WSEvents
from ..core.event_publisher import EventPublisher
from ..core.event_bus import event_bus, EventType

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
            channel_metadata: Metadados adicionais (será passado como event_metadata)
        
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
                event_metadata=channel_metadata
            )
            
            # Nota: Notificação kanban foi movida para quando o pedido é marcado como impresso
            # Não enviamos mais notificação kanban na criação do pedido
            logger.debug(f"[NOTIFY] Evento de novo pedido criado: {pedido_id} para empresa {empresa_id}")
            
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
                event_metadata=channel_metadata
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
            # Metadados opcionais (ajuda o frontend a montar "resumo" e refetch)
            tipo_entrega = (channel_metadata or {}).get("tipo_entrega")
            numero_pedido = (channel_metadata or {}).get("numero_pedido")
            status_atual = (channel_metadata or {}).get("status")

            # Publica o evento
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type=EventType.PEDIDO_CANCELADO,
                data={
                    "pedido_id": pedido_id,
                    "motivo": motivo,
                    "cancelado_por": cancelado_por,
                    "status": "cancelado",
                    "tipo_entrega": tipo_entrega,
                    "numero_pedido": numero_pedido,
                },
                event_id=pedido_id,
                event_metadata=channel_metadata
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
                    "tipo_entrega": tipo_entrega,
                    "numero_pedido": numero_pedido,
                    "status": status_atual or "C",
                    "timestamp": datetime.utcnow().isoformat()
                },
                # Mantém o tráfego focado na tela de pedidos/kanban
                required_route="/pedidos",
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
                event_metadata=channel_metadata
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
    
    async def notify_pedido_impresso(
        self,
        empresa_id: str,
        pedido_id: str,
        cliente_data: Dict[str, Any],
        itens: list,
        valor_total: float,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Notifica sobre um pedido marcado como impresso (notificação kanban)
        
        Args:
            empresa_id: ID da empresa
            pedido_id: ID do pedido
            cliente_data: Dados do cliente
            itens: Lista de itens do pedido
            valor_total: Valor total do pedido
            channel_metadata: Metadados adicionais
        
        Returns:
            Número de conexões que receberam a notificação (0 se nenhuma)
        """
        try:
            # Metadados opcionais (ajuda o frontend a montar "resumo" e refetch)
            tipo_entrega = (channel_metadata or {}).get("tipo_entrega")
            numero_pedido = (channel_metadata or {}).get("numero_pedido")
            status_atual = (channel_metadata or {}).get("status")

            # Normaliza empresa_id para string
            empresa_id_normalized = str(empresa_id)
            
            logger.debug(
                f"[NOTIFY] Enviando notificação kanban para pedido impresso. "
                f"pedido_id={pedido_id}, empresa_id={empresa_id} (normalized={empresa_id_normalized})"
            )
            
            # Verifica se há empresa e clientes conectados
            is_connected = websocket_manager.is_empresa_connected(empresa_id_normalized)
            
            if not is_connected:
                logger.debug(
                    f"[NOTIFY] Notificação kanban não enviada: empresa {empresa_id_normalized} "
                    f"não tem conexões ativas. Pedido {pedido_id} impresso mas nenhum cliente conectado."
                )
                return 0
            
            # Envia notificação em tempo real via WebSocket apenas para clientes na rota /pedidos
            sent_count = await self._send_realtime_notification(
                empresa_id=empresa_id,
                notification_type="kanban",
                title="Novo Pedido Recebido",
                message=f"Pedido #{pedido_id} impresso - Valor: R$ {valor_total:.2f}",
                data={
                    "pedido_id": pedido_id,
                    "cliente": cliente_data,
                    "valor_total": valor_total,
                    "itens_count": len(itens),
                    "tipo_entrega": tipo_entrega,
                    "numero_pedido": numero_pedido,
                    "status": status_atual,
                    "timestamp": datetime.utcnow().isoformat()
                },
                required_route="/pedidos"
            )
            
            if sent_count > 0:
                logger.info(f"Notificação kanban enviada: {pedido_id} para empresa {empresa_id} ({sent_count} conexões na rota /pedidos)")
            else:
                logger.info(
                    f"Notificação kanban não enviada: {pedido_id} para empresa {empresa_id}. "
                    f"Nenhum cliente conectado na rota /pedidos."
                )
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Erro ao notificar pedido impresso {pedido_id}: {e}", exc_info=True)
            return 0
    
    async def _send_realtime_notification(
        self,
        empresa_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        required_route: Optional[str] = None
    ) -> int:
        """Envia notificação em tempo real via WebSocket
        
        Args:
            empresa_id: ID da empresa
            notification_type: Tipo da notificação
            title: Título da notificação
            message: Mensagem da notificação
            data: Dados adicionais
            required_route: Rota que o cliente deve estar para receber (None = envia para todos)
        
        Returns:
            Número de conexões que receberam a notificação (0 se nenhuma)
        """
        try:
            # Normaliza empresa_id para string
            empresa_id = str(empresa_id)
            
            notification_data = {
                "type": "notification",
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "data": data,
                "empresa_id": empresa_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Emite também o evento padronizado (compatível com o novo contrato),
            # mantendo o formato antigo acima para não quebrar consumidores legados.
            event_map = {
                "kanban": WSEvents.PEDIDO_IMPRESSO,
                "pedido_aprovado": WSEvents.PEDIDO_APROVADO,
                "pedido_cancelado": WSEvents.PEDIDO_CANCELADO,
                "pedido_entregue": WSEvents.PEDIDO_ENTREGUE,
            }
            ws_event = event_map.get(notification_type)

            # Payload do evento (contrato novo). Mantém pedido_id e inclui metadados úteis se existirem.
            event_payload: Dict[str, Any] = {"pedido_id": data.get("pedido_id")}
            for k in ("tipo_entrega", "numero_pedido", "status"):
                if k in data and data.get(k) is not None:
                    event_payload[k] = data.get(k)
            
            # Se uma rota é requerida, envia apenas para clientes nessa rota
            if required_route:
                sent_count = await websocket_manager.send_to_empresa_on_route(
                    empresa_id, 
                    notification_data, 
                    required_route
                )
                if ws_event:
                    await websocket_manager.emit_event(
                        event=ws_event,
                        scope="empresa",
                        empresa_id=empresa_id,
                        payload=event_payload,
                        required_route=required_route,
                    )
            else:
                # Envia para todos os usuários da empresa conectados
                sent_count = await websocket_manager.send_to_empresa(empresa_id, notification_data)
                if ws_event:
                    await websocket_manager.emit_event(
                        event=ws_event,
                        scope="empresa",
                        empresa_id=empresa_id,
                        payload=event_payload,
                    )
            
            return sent_count
                
        except Exception as e:
            logger.error(f"Erro ao enviar notificação em tempo real: {e}", exc_info=True)
            # Retorna 0 em caso de erro
            return 0

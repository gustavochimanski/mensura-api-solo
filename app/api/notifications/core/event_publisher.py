from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging
from .event_bus import EventBus, Event, EventType

logger = logging.getLogger(__name__)

class EventPublisher:
    """Serviço para publicar eventos no sistema"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def publish_event(
        self,
        empresa_id: str,
        event_type: EventType,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publica um evento no sistema
        
        Args:
            empresa_id: ID da empresa
            event_type: Tipo do evento
            data: Dados do evento
            event_id: ID do recurso que gerou o evento (opcional)
            metadata: Metadados adicionais (opcional)
        
        Returns:
            ID do evento criado
        """
        event = Event(
            id=str(uuid.uuid4()),
            empresa_id=empresa_id,
            event_type=event_type,
            event_id=event_id,
            data=data,
            event_metadata=event_metadata or {},
            created_at=datetime.utcnow()
        )
        
        await self.event_bus.publish(event)
        
        logger.info(f"Evento publicado: {event_type} - {event.id} para empresa {empresa_id}")
        return event.id
    
    # Métodos de conveniência para eventos comuns
    
    async def publish_pedido_criado(
        self,
        empresa_id: str,
        pedido_id: str,
        cliente_data: Dict[str, Any],
        itens: list,
        valor_total: float,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publica evento de pedido criado"""
        data = {
            "pedido_id": pedido_id,
            "cliente": cliente_data,
            "itens": itens,
            "valor_total": valor_total,
            "status": "criado"
        }
        return await self.publish_event(
            empresa_id=empresa_id,
            event_type=EventType.PEDIDO_CRIADO,
            data=data,
            event_id=pedido_id,
            event_metadata=event_metadata
        )
    
    async def publish_pedido_aprovado(
        self,
        empresa_id: str,
        pedido_id: str,
        aprovado_por: str,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publica evento de pedido aprovado"""
        data = {
            "pedido_id": pedido_id,
            "aprovado_por": aprovado_por,
            "status": "aprovado"
        }
        return await self.publish_event(
            empresa_id=empresa_id,
            event_type=EventType.PEDIDO_APROVADO,
            data=data,
            event_id=pedido_id,
            event_metadata=event_metadata
        )
    
    async def publish_estoque_baixo(
        self,
        empresa_id: str,
        produto_id: str,
        produto_nome: str,
        quantidade_atual: int,
        quantidade_minima: int,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publica evento de estoque baixo"""
        data = {
            "produto_id": produto_id,
            "produto_nome": produto_nome,
            "quantidade_atual": quantidade_atual,
            "quantidade_minima": quantidade_minima,
            "status": "estoque_baixo"
        }
        return await self.publish_event(
            empresa_id=empresa_id,
            event_type=EventType.ESTOQUE_BAIXO,
            data=data,
            event_id=produto_id,
            event_metadata=event_metadata
        )
    
    async def publish_pagamento_aprovado(
        self,
        empresa_id: str,
        pagamento_id: str,
        pedido_id: str,
        valor: float,
        metodo_pagamento: str,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publica evento de pagamento aprovado"""
        data = {
            "pagamento_id": pagamento_id,
            "pedido_id": pedido_id,
            "valor": valor,
            "metodo_pagamento": metodo_pagamento,
            "status": "aprovado"
        }
        return await self.publish_event(
            empresa_id=empresa_id,
            event_type=EventType.PAGAMENTO_APROVADO,
            data=data,
            event_id=pagamento_id,
            event_metadata=event_metadata
        )
    
    async def publish_sistema_erro(
        self,
        empresa_id: str,
        erro: str,
        modulo: str,
        severidade: str = "error",
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publica evento de erro do sistema"""
        data = {
            "erro": erro,
            "modulo": modulo,
            "severidade": severidade,
            "status": "erro"
        }
        return await self.publish_event(
            empresa_id=empresa_id,
            event_type=EventType.SISTEMA_ERRO,
            data=data,
            event_metadata=event_metadata
        )

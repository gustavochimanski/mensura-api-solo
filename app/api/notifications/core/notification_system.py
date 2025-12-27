import asyncio
import logging
from typing import Optional
from datetime import datetime

from .event_bus import event_bus
from .websocket_manager import websocket_manager
from ..services.event_processor import EventProcessor
from ..repositories.event_repository import EventRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)

class NotificationSystem:
    """Sistema principal de notificações"""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.event_processor: Optional[EventProcessor] = None
        self._running = False
    
    async def initialize(self):
        """Inicializa o sistema de notificações"""
        try:
            logger.info("Inicializando sistema de notificações...")
            
            # Cria repositórios
            event_repo = EventRepository(self.db_session)
            subscription_repo = SubscriptionRepository(self.db_session)
            notification_repo = NotificationRepository(self.db_session)
            
            # Cria processador de eventos
            self.event_processor = EventProcessor(
                event_repo, subscription_repo, notification_repo
            )
            
            # Registra o processador de eventos no event bus
            event_bus.subscribe("pedido_criado", self.event_processor)
            event_bus.subscribe("pedido_aprovado", self.event_processor)
            event_bus.subscribe("pedido_cancelado", self.event_processor)
            event_bus.subscribe("pedido_entregue", self.event_processor)
            event_bus.subscribe("estoque_baixo", self.event_processor)
            event_bus.subscribe("pagamento_aprovado", self.event_processor)
            event_bus.subscribe("sistema_erro", self.event_processor)
            
            # Inicia o event bus
            await event_bus.start()
            
            self._running = True
            logger.info("Sistema de notificações inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar sistema de notificações: {e}")
            # Não levanta exceção para não quebrar a aplicação
            self._running = False
    
    async def shutdown(self):
        """Para o sistema de notificações"""
        try:
            logger.info("Parando sistema de notificações...")
            
            self._running = False
            
            # Para o event bus
            await event_bus.stop()
            
            logger.info("Sistema de notificações parado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao parar sistema de notificações: {e}")
    
    def get_connection_stats(self):
        """Retorna estatísticas das conexões WebSocket"""
        return websocket_manager.get_connection_stats()
    
    def is_user_connected(self, user_id: str) -> bool:
        """Verifica se um usuário está conectado"""
        return websocket_manager.is_user_connected(user_id)
    
    async def send_notification_to_user(self, user_id: str, title: str, message: str, data: dict = None):
        """Envia notificação para um usuário específico"""
        notification_data = {
            "type": "notification",
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await websocket_manager.send_to_user(user_id, notification_data)
    
    async def send_notification_to_empresa(self, empresa_id: str, title: str, message: str, data: dict = None):
        """Envia notificação para todos os usuários de uma empresa"""
        notification_data = {
            "type": "notification",
            "title": title,
            "message": message,
            "data": data or {},
            "empresa_id": empresa_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await websocket_manager.send_to_empresa(empresa_id, notification_data)

# Instância global do sistema de notificações
notification_system: Optional[NotificationSystem] = None

async def initialize_notification_system(db_session):
    """Inicializa o sistema de notificações globalmente"""
    global notification_system
    notification_system = NotificationSystem(db_session)
    await notification_system.initialize()
    return notification_system

async def shutdown_notification_system():
    """Para o sistema de notificações globalmente"""
    global notification_system
    if notification_system:
        await notification_system.shutdown()
        notification_system = None

def get_notification_system() -> Optional[NotificationSystem]:
    """Retorna a instância do sistema de notificações"""
    return notification_system

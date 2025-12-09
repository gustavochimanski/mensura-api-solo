"""Contratos para repositórios"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..models.notification import Notification, NotificationLog, NotificationStatus
from ..schemas.notification_schemas import NotificationFilter

class INotificationRepository(ABC):
    """Interface para repositório de notificações"""
    
    @abstractmethod
    def create(self, notification_data: Dict[str, Any]) -> Notification:
        """Cria uma nova notificação"""
        pass
    
    @abstractmethod
    def get_by_id(self, notification_id: str) -> Optional[Notification]:
        """Busca notificação por ID"""
        pass
    
    @abstractmethod
    def get_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0) -> List[Notification]:
        """Busca notificações por empresa"""
        pass
    
    @abstractmethod
    def get_pending_notifications(self, limit: int = 100) -> List[Notification]:
        """Busca notificações pendentes para processamento"""
        pass
    
    @abstractmethod
    def update_status(
        self,
        notification_id: str,
        status: NotificationStatus,
        attempts: Optional[int] = None,
        next_retry_at: Optional[datetime] = None
    ) -> bool:
        """Atualiza status da notificação"""
        pass
    
    @abstractmethod
    def add_log(
        self,
        notification_id: str,
        status: NotificationStatus,
        message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Adiciona log à notificação"""
        pass
    
    @abstractmethod
    def filter_notifications(
        self,
        filters: NotificationFilter,
        limit: int = 100,
        offset: int = 0
    ) -> List[Notification]:
        """Filtra notificações com base nos critérios fornecidos"""
        pass

class ISubscriptionRepository(ABC):
    """Interface para repositório de assinaturas"""
    
    @abstractmethod
    def create(self, subscription_data: Dict[str, Any]):
        """Cria uma nova assinatura"""
        pass
    
    @abstractmethod
    def get_by_empresa(self, empresa_id: str):
        """Busca assinaturas por empresa"""
        pass

class IEventRepository(ABC):
    """Interface para repositório de eventos"""
    
    @abstractmethod
    def create(self, event_data: Dict[str, Any]):
        """Cria um novo evento"""
        pass
    
    @abstractmethod
    def get_unprocessed_events(self, limit: int = 100):
        """Busca eventos não processados"""
        pass


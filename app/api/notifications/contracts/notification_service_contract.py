"""Contrato para o serviço de notificações"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..schemas.notification_schemas import (
    CreateNotificationRequest,
    SendNotificationRequest
)

class INotificationService(ABC):
    """Interface para o serviço de notificações"""
    
    @abstractmethod
    async def create_notification(self, request: CreateNotificationRequest) -> str:
        """
        Cria uma nova notificação
        
        Args:
            request: Dados da notificação
            
        Returns:
            ID da notificação criada
        """
        pass
    
    @abstractmethod
    async def send_notification(self, request: SendNotificationRequest) -> List[str]:
        """
        Envia notificação para múltiplos canais
        
        Args:
            request: Dados da notificação
            
        Returns:
            Lista de IDs das notificações criadas
        """
        pass
    
    @abstractmethod
    async def process_pending_notifications(self, limit: int = 50):
        """Processa notificações pendentes"""
        pass
    
    @abstractmethod
    async def retry_failed_notifications(self, limit: int = 50):
        """Tenta reenviar notificações que falharam"""
        pass
    
    @abstractmethod
    def get_notification_by_id(self, notification_id: str):
        """Busca notificação por ID"""
        pass
    
    @abstractmethod
    def get_notifications_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0):
        """Busca notificações por empresa"""
        pass
    
    @abstractmethod
    def get_notification_logs(self, notification_id: str):
        """Busca logs de uma notificação"""
        pass


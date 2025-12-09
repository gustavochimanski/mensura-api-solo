"""Contrato para provedor de configurações de canais"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models.notification import NotificationChannel

class IChannelConfigProvider(ABC):
    """Interface para provedor de configurações de canais de notificação"""
    
    @abstractmethod
    def get_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel
    ) -> Optional[Dict[str, Any]]:
        """
        Busca configuração do canal para a empresa
        
        Args:
            empresa_id: ID da empresa
            channel: Canal de notificação
            
        Returns:
            Dicionário com configuração do canal ou None se não encontrado
        """
        pass
    
    @abstractmethod
    def validate_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel,
        config: Dict[str, Any]
    ) -> bool:
        """
        Valida uma configuração de canal
        
        Args:
            empresa_id: ID da empresa
            channel: Canal de notificação
            config: Configuração a validar
            
        Returns:
            True se a configuração é válida
        """
        pass
    
    @abstractmethod
    def get_default_channel_config(self, channel: NotificationChannel) -> Dict[str, Any]:
        """
        Retorna configuração padrão para um canal
        
        Args:
            channel: Canal de notificação
            
        Returns:
            Dicionário com configuração padrão
        """
        pass


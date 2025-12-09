"""Adaptadores para provedores de configuração de canais"""

from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.orm import Session

from ..contracts.channel_config_provider_contract import IChannelConfigProvider
from ..models.notification import NotificationChannel

logger = logging.getLogger(__name__)

class DefaultChannelConfigAdapter(IChannelConfigProvider):
    """Adaptador que retorna configurações padrão para canais"""
    
    def get_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel
    ) -> Optional[Dict[str, Any]]:
        """Retorna configuração padrão baseada no canal"""
        return self.get_default_channel_config(channel)
    
    def validate_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel,
        config: Dict[str, Any]
    ) -> bool:
        """Valida configuração básica"""
        if channel == NotificationChannel.EMAIL:
            return 'username' in config and 'password' in config
        elif channel == NotificationChannel.WHATSAPP:
            return all(k in config for k in ['account_sid', 'auth_token', 'from_number'])
        elif channel == NotificationChannel.WEBHOOK:
            return 'url' in config or 'endpoint' in config
        elif channel == NotificationChannel.PUSH:
            return 'server_key' in config or 'api_key' in config
        return True
    
    def get_default_channel_config(self, channel: NotificationChannel) -> Dict[str, Any]:
        """Retorna configuração padrão para um canal"""
        default_configs = {
            NotificationChannel.EMAIL: {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "noreply@mensura.com.br",
                "password": "your_password_here",
                "from_email": "noreply@mensura.com.br",
                "from_name": "Sistema Mensura"
            },
            NotificationChannel.WEBHOOK: {
                "timeout": 30,
                "headers": {"Content-Type": "application/json"}
            },
            NotificationChannel.WHATSAPP: {
                "account_sid": "your_twilio_sid",
                "auth_token": "your_twilio_token",
                "from_number": "+1234567890"
            },
            NotificationChannel.PUSH: {
                "server_key": "your_firebase_server_key"
            },
            NotificationChannel.IN_APP: {
                "websocket_enabled": True
            }
        }
        
        return default_configs.get(channel, {})

class DatabaseChannelConfigAdapter(IChannelConfigProvider):
    """Adaptador que busca configurações do banco de dados"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel
    ) -> Optional[Dict[str, Any]]:
        """Busca configuração do banco de dados"""
        # TODO: Implementar busca real no banco
        # Por enquanto, retorna None para usar configuração padrão
        logger.debug(f"Buscando configuração de canal {channel} para empresa {empresa_id}")
        return None
    
    def validate_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel,
        config: Dict[str, Any]
    ) -> bool:
        """Valida configuração"""
        # TODO: Implementar validação baseada em regras do banco
        return True
    
    def get_default_channel_config(self, channel: NotificationChannel) -> Dict[str, Any]:
        """Retorna configuração padrão"""
        default_adapter = DefaultChannelConfigAdapter()
        return default_adapter.get_default_channel_config(channel)

class CompositeChannelConfigAdapter(IChannelConfigProvider):
    """Adaptador composto que tenta múltiplos adaptadores"""
    
    def __init__(self, adapters: List[IChannelConfigProvider]):
        self.adapters = adapters
    
    def get_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel
    ) -> Optional[Dict[str, Any]]:
        """Tenta buscar em todos os adaptadores até encontrar"""
        for adapter in self.adapters:
            config = adapter.get_channel_config(empresa_id, channel)
            if config:
                return config
        return None
    
    def validate_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel,
        config: Dict[str, Any]
    ) -> bool:
        """Valida usando o primeiro adaptador disponível"""
        for adapter in self.adapters:
            if hasattr(adapter, 'validate_channel_config'):
                return adapter.validate_channel_config(empresa_id, channel, config)
        return True
    
    def get_default_channel_config(self, channel: NotificationChannel) -> Dict[str, Any]:
        """Retorna configuração padrão do primeiro adaptador"""
        for adapter in self.adapters:
            if hasattr(adapter, 'get_default_channel_config'):
                return adapter.get_default_channel_config(channel)
        return {}


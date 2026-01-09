"""Adaptadores para provedores de configuração de canais"""

from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.orm import Session

from ..contracts.channel_config_provider_contract import IChannelConfigProvider
from ..models.notification import NotificationChannel
from ..repositories.whatsapp_config_repository import WhatsAppConfigRepository

logger = logging.getLogger(__name__)

class DefaultChannelConfigAdapter(IChannelConfigProvider):
    """Adaptador que retorna configurações padrão para canais"""
    
    def get_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel
    ) -> Optional[Dict[str, Any]]:
        """Retorna configuração padrão baseada no canal"""
        config = self.get_default_channel_config(channel)
        
        # Para WhatsApp, tenta usar a configuração do chatbot se disponível
        if channel == NotificationChannel.WHATSAPP:
            try:
                from app.api.chatbot.core.config_whatsapp import load_whatsapp_config
                chatbot_config = load_whatsapp_config(empresa_id)
                if chatbot_config.get("access_token") and chatbot_config.get("phone_number_id"):
                    config = {
                        "access_token": chatbot_config.get("access_token"),
                        "phone_number_id": chatbot_config.get("phone_number_id"),
                        "api_version": chatbot_config.get("api_version", "v22.0")
                    }
                    logger.debug("Usando configuração do WhatsApp do chatbot")
            except ImportError:
                # Se o módulo do chatbot não estiver disponível, usa a configuração padrão
                pass
            except Exception as e:
                logger.warning(f"Erro ao buscar configuração do WhatsApp do chatbot: {e}")
        
        return config
    
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
            # 360dialog precisa apenas da api key; Meta Cloud requer phone_number_id
            if "360dialog" in str(config.get("base_url", "")):
                return bool(config.get("access_token"))
            return all(k in config for k in ['access_token', 'phone_number_id'])
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
                # Usa 360dialog como padrão, mas depende da configuração por empresa
                "base_url": "https://waba-v2.360dialog.io",
                "provider": "360dialog",
                "api_version": "v22.0",
                "send_mode": "api"
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
        self.whatsapp_repo = WhatsAppConfigRepository(db)
    
    def get_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel
    ) -> Optional[Dict[str, Any]]:
        """Busca configuração do banco de dados"""
        logger.debug(f"Buscando configuração de canal {channel} para empresa {empresa_id}")

        if channel == NotificationChannel.WHATSAPP:
            config = self.whatsapp_repo.get_active_by_empresa(empresa_id)
            if not config:
                return None

            return {
                "access_token": config.access_token,
                "phone_number_id": config.phone_number_id,
                "business_account_id": config.business_account_id,
                "api_version": config.api_version,
                "send_mode": config.send_mode,
                "coexistence_enabled": config.coexistence_enabled,
                "display_phone_number": config.display_phone_number,
                "name": config.name,
                    "base_url": config.base_url or "https://waba-v2.360dialog.io",
                    "provider": config.provider or "360dialog",
                    "webhook_url": config.webhook_url,
                    "webhook_verify_token": config.webhook_verify_token,
                    "webhook_is_active": config.webhook_is_active,
                    "webhook_status": config.webhook_status,
                    "webhook_last_sync": config.webhook_last_sync,
            }

        return None
    
    def validate_channel_config(
        self,
        empresa_id: str,
        channel: NotificationChannel,
        config: Dict[str, Any]
    ) -> bool:
        """Valida configuração"""
        if channel == NotificationChannel.WHATSAPP:
            if "360dialog" in str(config.get("base_url", "")):
                return bool(config.get("access_token"))
            return all(config.get(k) for k in ("access_token", "phone_number_id"))
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


from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel
from .email_channel import EmailChannel
from .webhook_channel import WebhookChannel
from .whatsapp_channel import WhatsAppChannel
from .push_channel import PushChannel
from .in_app_channel import InAppChannel

logger = logging.getLogger(__name__)

class ChannelFactory:
    """Factory para criar canais de notificação"""
    
    _channels = {
        'email': EmailChannel,
        'webhook': WebhookChannel,
        'whatsapp': WhatsAppChannel,
        'push': PushChannel,
        'in_app': InAppChannel,
    }
    
    @classmethod
    def create_channel(cls, channel_type: str, config: Dict[str, Any]) -> BaseNotificationChannel:
        """
        Cria um canal de notificação
        
        Args:
            channel_type: Tipo do canal (email, webhook, whatsapp, push, in_app)
            config: Configuração do canal
        
        Returns:
            Instância do canal de notificação
        
        Raises:
            ValueError: Se o tipo de canal não for suportado
        """
        if channel_type not in cls._channels:
            supported_channels = ', '.join(cls._channels.keys())
            raise ValueError(f"Canal '{channel_type}' não suportado. Canais disponíveis: {supported_channels}")
        
        try:
            channel_class = cls._channels[channel_type]
            return channel_class(config)
        except Exception as e:
            logger.error(f"Erro ao criar canal {channel_type}: {e}")
            raise ValueError(f"Erro ao criar canal {channel_type}: {str(e)}")
    
    @classmethod
    def get_supported_channels(cls) -> list:
        """Retorna lista de canais suportados"""
        return list(cls._channels.keys())
    
    @classmethod
    def validate_channel_config(cls, channel_type: str, config: Dict[str, Any]) -> bool:
        """
        Valida a configuração de um canal
        
        Args:
            channel_type: Tipo do canal
            config: Configuração do canal
        
        Returns:
            True se a configuração é válida
        """
        if channel_type not in cls._channels:
            return False
        
        try:
            channel_class = cls._channels[channel_type]
            # Cria uma instância temporária para validar
            temp_channel = channel_class(config)
            return temp_channel.validate_config(config)
        except Exception:
            return False

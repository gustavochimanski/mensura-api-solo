"""Contratos (interfaces) para o sistema de notificações"""

from .notification_service_contract import INotificationService
from .message_dispatch_service_contract import IMessageDispatchService
from .recipient_provider_contract import IRecipientProvider
from .channel_config_provider_contract import IChannelConfigProvider
from .repository_contracts import (
    INotificationRepository,
    ISubscriptionRepository,
    IEventRepository
)

__all__ = [
    "INotificationService",
    "IMessageDispatchService",
    "IRecipientProvider",
    "IChannelConfigProvider",
    "INotificationRepository",
    "ISubscriptionRepository",
    "IEventRepository"
]


"""Adaptadores para o sistema de notificações"""

from .recipient_adapters import (
    ClienteRecipientAdapter,
    UserRecipientAdapter,
    CompositeRecipientAdapter
)
from .channel_config_adapters import (
    DatabaseChannelConfigAdapter,
    DefaultChannelConfigAdapter,
    CompositeChannelConfigAdapter
)

__all__ = [
    "ClienteRecipientAdapter",
    "UserRecipientAdapter",
    "CompositeRecipientAdapter",
    "DatabaseChannelConfigAdapter",
    "DefaultChannelConfigAdapter",
    "CompositeChannelConfigAdapter"
]


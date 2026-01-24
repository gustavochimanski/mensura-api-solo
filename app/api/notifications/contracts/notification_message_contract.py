from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class INotificationMessageContract(ABC):
    """
    Contract para construção de payloads por canal a partir de conteúdo (title/message)
    e metadados específicos do canal (channel_metadata).

    Objetivo:
    - Centralizar a transformação do "conteúdo de notificação" em payload do provedor.
    - Permitir suportar "template messages" no WhatsApp (necessário sem janela de conversa).
    """

    @abstractmethod
    def build_whatsapp_payload(
        self,
        *,
        recipient_phone: str,
        title: str,
        message: str,
        is_360: bool,
        channel_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Monta o payload de envio do WhatsApp (360dialog ou Meta Cloud)."""
        raise NotImplementedError

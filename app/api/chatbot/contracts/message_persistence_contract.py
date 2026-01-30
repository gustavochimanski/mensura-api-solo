from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ChatMessageSourceType(str, Enum):
    """
    Tipo/origem da mensagem para auditoria e roteamento.

    Pedidos do projeto:
    - IA: mensagem gerada pelo bot (LLM)
    - WHATSAPP_WEB: mensagem enviada por humano via WhatsApp Web/app (capturada no webhook como outgoing)
    - WHATSAPP_NOTIFICATION: mensagem enviada via endpoint /send-notification (normalmente humano no painel)
    """

    IA = "IA"
    WHATSAPP_WEB = "WHATSAPP_WEB"
    WHATSAPP_NOTIFICATION = "WHATSAPP_NOTIFICATION"

    # Para robustez/compatibilidade futura
    WHATSAPP_INBOUND_CLIENT = "WHATSAPP_INBOUND_CLIENT"
    SYSTEM = "SYSTEM"
    UNKNOWN = "UNKNOWN"


class ChatMessageSenderType(str, Enum):
    """Quem 'falou' do ponto de vista do sistema."""

    HUMAN = "HUMAN"
    AI = "AI"
    CLIENT = "CLIENT"
    SYSTEM = "SYSTEM"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PersistChatMessageCommand:
    conversation_id: int
    role: str  # 'user' ou 'assistant' (compatível com schema atual)
    content: str
    empresa_id: Optional[int] = None
    whatsapp_message_id: Optional[str] = None
    source_type: ChatMessageSourceType = ChatMessageSourceType.UNKNOWN
    sender_type: ChatMessageSenderType = ChatMessageSenderType.UNKNOWN
    metadata: Optional[Dict[str, Any]] = None


class IChatMessagePersistenceContract(ABC):
    """
    Port de persistência de mensagens (DDD).

    Objetivo: centralizar regras de gravação (metadata padronizada + idempotência),
    para que *todas* as mensagens passem por um único fluxo.
    """

    @abstractmethod
    def persist_message(self, cmd: PersistChatMessageCommand) -> Optional[int]:
        """Persiste uma mensagem e retorna o ID, se possível."""
        raise NotImplementedError


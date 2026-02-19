from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..contracts.message_persistence_contract import (
    ChatMessageSenderType,
    ChatMessageSourceType,
    IChatMessagePersistenceContract,
    PersistChatMessageCommand,
)


class ChatMessagePersistenceAdapter(IChatMessagePersistenceContract):
    """
    Adapter de persistência de mensagens (infra).

    Responsabilidades:
    - Centralizar metadata padronizada (source_type/sender_type/empresa_id)
    - Idempotência quando houver whatsapp_message_id
    - Degradação graciosa (não quebrar fluxo do webhook)
    """

    def __init__(self, db: Session):
        self.db = db

    def _find_existing_by_whatsapp_message_id(
        self, *, conversation_id: int, whatsapp_message_id: str
    ) -> Optional[int]:
        """
        Retorna ID da mensagem se já existir metadata.whatsapp_message_id igual.

        Observação: não existe UNIQUE constraint no schema atual; por isso checamos aqui.
        """
        try:
            q = text(
                """
                SELECT id
                FROM chatbot.messages
                WHERE conversation_id = :conversation_id
                  AND metadata ->> 'whatsapp_message_id' = :whatsapp_message_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = self.db.execute(
                q,
                {"conversation_id": int(conversation_id), "whatsapp_message_id": str(whatsapp_message_id)},
            ).fetchone()
            return int(row[0]) if row else None
        except Exception:
            return None

    def persist_message(self, cmd: PersistChatMessageCommand) -> Optional[int]:
        from app.api.chatbot.core import database as chatbot_db

        if not cmd or not cmd.conversation_id or not cmd.role:
            return None

        content = (cmd.content or "").strip()
        if content == "":
            # Não salva mensagem vazia
            return None

        # Idempotência por whatsapp_message_id (quando existir)
        if cmd.whatsapp_message_id:
            existing_id = self._find_existing_by_whatsapp_message_id(
                conversation_id=cmd.conversation_id, whatsapp_message_id=cmd.whatsapp_message_id
            )
            if existing_id:
                return existing_id

        # Metadata padronizada
        extra: Dict[str, Any] = {}
        extra["source_type"] = (cmd.source_type or ChatMessageSourceType.UNKNOWN).value
        extra["sender_type"] = (cmd.sender_type or ChatMessageSenderType.UNKNOWN).value
        if cmd.empresa_id is not None:
            extra["empresa_id"] = int(cmd.empresa_id)
        if cmd.metadata and isinstance(cmd.metadata, dict):
            # cmd.metadata tem precedência sobre defaults, mas não remove os padrões
            extra.update(cmd.metadata)

        try:
            return chatbot_db.create_message(
                db=self.db,
                conversation_id=int(cmd.conversation_id),
                role=str(cmd.role),
                content=content,
                whatsapp_message_id=str(cmd.whatsapp_message_id) if cmd.whatsapp_message_id else None,
                extra_metadata=extra,
            )
        except Exception:
            # tenta rollback e reexecuta (create_message já tenta, mas aqui é um último "cinto e suspensório")
            try:
                self.db.rollback()
            except Exception:
                pass
            try:
                return chatbot_db.create_message(
                    db=self.db,
                    conversation_id=int(cmd.conversation_id),
                    role=str(cmd.role),
                    content=content,
                    whatsapp_message_id=str(cmd.whatsapp_message_id) if cmd.whatsapp_message_id else None,
                    extra_metadata=extra,
                )
            except Exception:
                return None


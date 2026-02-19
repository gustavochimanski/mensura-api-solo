"""
Repository de Conversa (Infrastructure).

Centraliza leitura/gravação do estado da conversa em `chatbot.conversations`
e carregamento de histórico (mensagens) quando necessário.

Implementação baseada no comportamento atual do `GroqSalesHandler`, para migração sem regressão.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


class ConversaRepository:
    def __init__(self, db: Session, *, empresa_id: int, prompt_key: str, model: str = "llama-3.1-8b-instant"):
        self.db = db
        self.empresa_id = empresa_id
        self.prompt_key = prompt_key
        self.model = model

    def obter_estado(self, user_id: str, *, estado_padrao: str = "welcome") -> Tuple[str, Dict[str, Any]]:
        """
        Obtém (estado, dados) do metadata (sales_state / sales_data).
        Se existir conversation_id e não houver histórico, tenta carregar as últimas mensagens.
        """
        try:
            query = text(
                """
                SELECT id, metadata
                FROM chatbot.conversations
                WHERE user_id = :user_id AND empresa_id = :empresa_id
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
            result = self.db.execute(
                query, {"user_id": user_id, "empresa_id": self.empresa_id}
            ).fetchone()

            conversation_id = None
            estado = estado_padrao
            dados: Dict[str, Any] = {"carrinho": [], "historico": []}

            if result:
                conversation_id = result[0]
                metadata = result[1] or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except Exception:
                        metadata = {}

                if isinstance(metadata, dict):
                    estado = metadata.get("sales_state", estado_padrao)
                    dados = metadata.get("sales_data", {}) or {}

            if not isinstance(dados, dict):
                dados = {}

            dados.setdefault("carrinho", [])
            dados.setdefault("historico", [])

            if conversation_id and not dados.get("historico"):
                try:
                    from .. import database as chatbot_db

                    mensagens = chatbot_db.get_messages(self.db, conversation_id)
                    if mensagens:
                        dados["historico"] = [
                            {"role": m.get("role", "user"), "content": m.get("content", "")}
                            for m in mensagens[-10:]
                        ]
                except Exception:
                    # silêncio deliberado para não quebrar o fluxo em produção
                    pass

            return estado, dados
        except Exception:
            return estado_padrao, {"carrinho": [], "historico": []}

    def salvar_estado(self, user_id: str, estado: str, dados: Dict[str, Any]) -> None:
        """
        Salva estado da conversa (atualiza o mais recente; se não existir, cria novo).
        """
        try:
            dados_json = json.dumps(dados, ensure_ascii=False)

            query_update = text(
                """
                UPDATE chatbot.conversations
                SET
                    metadata = jsonb_build_object(
                        'sales_state', CAST(:estado AS text),
                        'sales_data', CAST(:dados AS jsonb)
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id AND empresa_id = :empresa_id
                AND id = (
                    SELECT id FROM chatbot.conversations
                    WHERE user_id = :user_id AND empresa_id = :empresa_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                RETURNING id
                """
            )

            result = self.db.execute(
                query_update,
                {
                    "estado": estado,
                    "dados": dados_json,
                    "user_id": user_id,
                    "empresa_id": self.empresa_id,
                },
            )
            updated_row = result.fetchone()

            if not updated_row:
                import uuid

                session_id = str(uuid.uuid4())
                query_insert = text(
                    """
                    INSERT INTO chatbot.conversations
                    (session_id, user_id, empresa_id, model, prompt_key, metadata, created_at, updated_at)
                    VALUES
                    (:session_id, :user_id, :empresa_id, :model, :prompt_key,
                     jsonb_build_object('sales_state', CAST(:estado AS text), 'sales_data', CAST(:dados AS jsonb)),
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                )
                self.db.execute(
                    query_insert,
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "empresa_id": self.empresa_id,
                        "model": self.model,
                        "prompt_key": self.prompt_key,
                        "estado": estado,
                        "dados": dados_json,
                    },
                )

            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

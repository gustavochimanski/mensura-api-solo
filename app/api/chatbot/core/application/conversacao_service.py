"""
Application Service de Conversação.

Orquestra leitura/gravação de estado da conversa e pequenas transições de fluxo.
Este serviço é intencionalmente “magro”: regras específicas devem ficar no domínio,
e I/O (DB) deve ficar em infrastructure.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from sqlalchemy.orm import Session

from ..infrastructure.conversa_repository import ConversaRepository


class ConversacaoService:
    def __init__(self, db: Session, *, empresa_id: int, prompt_key: str):
        self.repo = ConversaRepository(db, empresa_id=empresa_id, prompt_key=prompt_key)

    def obter_estado(self, user_id: str) -> Tuple[str, Dict[str, Any]]:
        return self.repo.obter_estado(user_id)

    def salvar_estado(self, user_id: str, estado: str, dados: Dict[str, Any]) -> None:
        self.repo.salvar_estado(user_id, estado, dados)

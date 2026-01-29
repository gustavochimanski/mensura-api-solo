from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Optional, Tuple

# Contexto por request (thread/task-local) para RLS no Postgres.
_rls_user_id: ContextVar[Optional[int]] = ContextVar("rls_user_id", default=None)
_rls_empresa_id: ContextVar[Optional[int]] = ContextVar("rls_empresa_id", default=None)


def set_rls_context(user_id: Optional[int], empresa_id: Optional[int]) -> Tuple[Token, Token]:
    """
    Define o contexto RLS do request atual.
    Retorna tokens para permitir reset seguro no final do request.
    """
    t1 = _rls_user_id.set(user_id)
    t2 = _rls_empresa_id.set(empresa_id)
    return t1, t2


def reset_rls_context(tokens: Tuple[Token, Token]) -> None:
    t1, t2 = tokens
    _rls_user_id.reset(t1)
    _rls_empresa_id.reset(t2)


def get_rls_user_id() -> Optional[int]:
    return _rls_user_id.get()


def get_rls_empresa_id() -> Optional[int]:
    return _rls_empresa_id.get()


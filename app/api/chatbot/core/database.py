"""Shim module re-exporting the infrastructure database implementation.

This file re-exports the functions used by the rest of the application from
`app.api.chatbot.core.infrastructure.database` so callers can import
`app.api.chatbot.core.database` without changing existing import paths.
"""
from typing import Any, Optional

from .infrastructure import database as _db  # type: ignore

# Basic objects
SessionLocal = getattr(_db, "SessionLocal", None)
Base = getattr(_db, "Base", None)

def get_db(*args, **kwargs):
    """Return the DB session generator from infrastructure implementation."""
    fn = getattr(_db, "get_db", None)
    if fn is None:
        raise AttributeError("infrastructure.database.get_db not available")
    return fn(*args, **kwargs)

# Re-export commonly-used functions expected by callers.
def init_database(db: Any) -> Any:
    fn = getattr(_db, "init_database", None)
    if fn is None:
        raise AttributeError("infrastructure.database.init_database not available")
    return fn(db)

def seed_default_prompts(db: Any) -> Any:
    fn = getattr(_db, "seed_default_prompts", None)
    if fn is None:
        raise AttributeError("infrastructure.database.seed_default_prompts not available")
    return fn(db)

def get_global_bot_status(db: Any, empresa_id: Optional[int] = None) -> Any:
    fn = getattr(_db, "get_global_bot_status", None)
    if fn is None:
        raise AttributeError("infrastructure.database.get_global_bot_status not available")
    return fn(db, empresa_id=empresa_id)

# Generic pass-through for other helpers commonly used by the chatbot.
_pass_through_names = [
    "get_prompt",
    "create_prompt",
    "get_all_prompts",
    "get_bot_status",
    "set_bot_status",
    "get_conversation",
    "create_conversation",
    "create_message",
    "get_conversations_by_user",
    "get_conversation_with_messages",
    "get_stats",
    "seed_default_prompts",
]

for _name in _pass_through_names:
    if hasattr(_db, _name):
        globals()[_name] = getattr(_db, _name)

__all__ = ["SessionLocal", "Base", "get_db", "init_database", "seed_default_prompts", "get_global_bot_status"] + [n for n in _pass_through_names if n in globals()]


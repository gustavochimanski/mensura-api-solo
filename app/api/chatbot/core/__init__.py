"""Chatbot core package shims and re-exports.
Provides compatibility layer so callers can import `app.api.chatbot.core.<module>`.
"""
from . import notifications  # noqa: F401
from . import ngrok_manager  # noqa: F401
from . import config_whatsapp  # noqa: F401

# Re-export commonly used submodules (some are shims that delegate to infrastructure)
from . import database  # noqa: F401

__all__ = ["notifications", "ngrok_manager", "config_whatsapp", "database"]


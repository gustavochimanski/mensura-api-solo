"""Compatibility shim: re-export implementation from infrastructure subpackage."""
from .infrastructure.config_whatsapp import (  # noqa: F401
    load_whatsapp_config,
    format_phone_number,
    get_whatsapp_url,
    get_headers,
    WHATSAPP_CONFIG,
    DEFAULT_WHATSAPP_CONFIG,
)

__all__ = [
    "load_whatsapp_config",
    "format_phone_number",
    "get_whatsapp_url",
    "get_headers",
    "WHATSAPP_CONFIG",
    "DEFAULT_WHATSAPP_CONFIG",
]


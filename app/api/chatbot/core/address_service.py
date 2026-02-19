"""Stub for address/addressing service used by chatbot routes."""
from typing import Dict, Any

class ChatbotAddressService:
    def __init__(self, *args, **kwargs):
        pass

    def resolve_address(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # return payload unchanged as a safe default
        return payload or {}

__all__ = ["ChatbotAddressService"]


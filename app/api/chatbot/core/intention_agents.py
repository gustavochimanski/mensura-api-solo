"""Minimal intention_agents shim exposing IntentionRouter and IntentionType."""
from enum import Enum
from typing import Any

class IntentionType(str, Enum):
    UNKNOWN = "unknown"
    ORDER = "order"

class IntentionRouter:
    def __init__(self, *args, **kwargs):
        pass

    def route(self, text: str) -> IntentionType:
        return IntentionType.UNKNOWN

__all__ = ["IntentionRouter", "IntentionType"]


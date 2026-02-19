"""Minimal intention_agents shim exposing IntentionRouter and IntentionType.

This shim provides a tiny heuristic-based detector used during migration/tests.
It should be replaced by the full implementation when available.
"""
from enum import Enum
from typing import Any, Dict


class IntentionType(str, Enum):
    UNKNOWN = "unknown"
    ORDER = "order"
    VER_CARDAPIO = "ver_cardapio"


class IntentionRouter:
    def __init__(self, *args, **kwargs):
        # placeholder for dependency injection if needed
        pass

    def route(self, text: str) -> IntentionType:
        """Backward-compatible alias for older callers."""
        res = self.detect_intention(text, text or "")
        return res.get("intention", IntentionType.UNKNOWN)

    def detect_intention(self, original_text: str, normalized_text: str) -> Dict[str, Any]:
        """
        Detecta intenções simples por heurística.
        Retorna um dict com chaves possíveis:
        - "intention": IntentionType
        - "funcao": str (nome da função a executar, ex: "ver_cardapio")
        """
        txt = (normalized_text or original_text or "").lower()
        # heurísticas simples
        if any(k in txt for k in ("cardapio", "cardápio", "ver cardapio", "ver cardápio", "menu", "cardapío")):
            return {"intention": IntentionType.VER_CARDAPIO, "funcao": "ver_cardapio"}
        if any(k in txt for k in ("pedir", "quero pedir", "fazer pedido", "pedido")):
            return {"intention": IntentionType.ORDER, "funcao": "create_order"}
        return {"intention": IntentionType.UNKNOWN}


__all__ = ["IntentionRouter", "IntentionType"]


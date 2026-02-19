from typing import Any, Dict, List, Optional
from ..base import AgentBase, IntentResult

class IntentAgent(AgentBase):
    \"\"\"Agent responsável por mapear intenção do usuário para funções disponíveis.\"\"\"

    def __init__(self, available_functions: Optional[List[Dict[str, Any]]] = None):
        self.available_functions = available_functions or []

    def handle_intent(self, request: Dict[str, Any]) -> IntentResult:
        text = request.get(\"text\", \"\").lower()
        # Heurística simples: procurar palavras-chave ligadas a pedido/compra
        if any(k in text for k in [\"comprar\", \"pedido\", \"adicionar\", \"carrinho\", \"produto\"]):
            return IntentResult(\"create_order\", {\"matched\": True})
        # fallback - devolver intenção genérica para ser tratada pelas funções disponíveis
        return IntentResult(\"unknown\", {})

    # compat wrapper
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        res = self.handle_intent(request)
        return {\"intent\": res.intent, \"params\": res.params}

from typing import Any, Dict, List, Optional
from ..base import AgentBase, IntentResult

class IntentAgent(AgentBase):
    # Agent responsável por mapear intenção do usuário para funções disponíveis."

    def __init__(self, available_functions: Optional[List[Dict[str, Any]]] = None):
        self.available_functions = available_functions or []

    def handle_intent(self, request: Dict[str, Any]) -> IntentResult:
        text = request.get(\"text\", \"\").lower()
        # Heurística simples: procurar palavras-chave ligadas a pedido/compra
        if any(k in text for k in [\"comprar\", \"pedido\", \"pedido\", \"adicionar\", \"carrinho\", \"produto\"]):
            return IntentResult(\"create_order\", {\"matched\": True})
        # fallback - devolver intenção genérica para ser tratada pelas funções disponíveis
        return IntentResult(\"unknown\", {})

    # compat wrapper
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        res = self.handle_intent(request)
        return {\"intent\": res.intent, \"params\": res.params}


from typing import Any, Dict, List, Optional
from ..base import AgentBase, IntentResult
from ..adapters import MultiAgentAdapters

class IntentAgent(AgentBase):
    """Agente responsável por mapear a intenção do usuário para funções disponíveis."""

    def __init__(
        self,
        available_functions: Optional[List[Dict[str, Any]]] = None,
        adapters: Optional[MultiAgentAdapters] = None,
    ):
        self.available_functions = available_functions or []
        self.adapters = adapters or MultiAgentAdapters()

    def handle_intent(self, request: Dict[str, Any]) -> IntentResult:
        text = request.get("text", "").lower()
        # Heurística simples: procurar palavras-chave ligadas a pedido/compra
        if any(k in text for k in ["comprar", "pedido", "adicionar", "carrinho", "produto"]):
            return IntentResult("create_order", {"matched": True})
        # intenção ver cardápio
        if any(k in text for k in ["cardapio", "cardápio", "menu", "cardápio_link", "cardápio link"]):
            return IntentResult("ver_cardapio", {"matched": True})
        # fallback - devolver intenção genérica para ser tratada pelas funções disponíveis
        return IntentResult("unknown", {})

    # wrapper de compatibilidade
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        res = self.handle_intent(request)
        return {"intent": res.intent, "params": res.params}


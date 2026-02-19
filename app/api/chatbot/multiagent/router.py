from typing import Dict, Any, Optional
from .intent_agent import IntentAgent
from .faq_agent import FaqAgent
from .adapters import MultiAgentAdapters


class Router:
    """Roteador que orquestra os agentes de intenção e FAQ.

    Fluxo:
    - Se `request.force_faq` estiver True => chama FAQ.
    - Primeiro tenta resolver intenção via IntentAgent; se for diferente de 'unknown' retorna intenção.
    - Caso contrário, tenta responder via FaqAgent.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        adapters: Optional[MultiAgentAdapters] = None,
        available_functions: Optional[list] = None,
    ):
        self.config = config or {}
        self.adapters = adapters or MultiAgentAdapters()
        self.intent_agent = IntentAgent(available_functions=available_functions, adapters=self.adapters)
        self.faq_agent = FaqAgent(adapters=self.adapters)

    def route(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # permitir forçar FAQ via flag no request
        if request.get("force_faq"):
            resp = self.faq_agent.handle(request)
            return {"type": "faq", "response": resp}

        # tentar identificar intenção primeiro
        intent_res = self.intent_agent.handle_intent(request)
        if intent_res.intent and intent_res.intent != "unknown":
            return {"type": "intent", "intent": intent_res.intent, "params": intent_res.params}

        # fallback para FAQ
        faq_res = self.faq_agent.handle(request)
        return {"type": "faq", "response": faq_res}

    def register_intent_agent(self, agent: IntentAgent) -> None:
        """Substitui o agente de intenção (útil para testes ou hot-swap)."""
        self.intent_agent = agent

    def register_faq_agent(self, agent: FaqAgent) -> None:
        """Substitui o agente de FAQ."""
        self.faq_agent = agent


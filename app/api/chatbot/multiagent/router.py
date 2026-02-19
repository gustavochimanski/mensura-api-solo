from typing import Dict, Any
from .intent_agent import IntentAgent
from .faq_agent import FaqAgent

class Router:
    \"\"\"Roteador simples que escolhe entre IntentAgent e FaqAgent.\"\"\"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.intent_agent = IntentAgent()
        self.faq_agent = FaqAgent()

    def route(self, request: Dict[str, Any]) -> Dict[str, Any]:
        text = request.get(\"text\", \"\").lower()
        faq_keywords = [\"horário\", \"horario\", \"preço\", \"preco\", \"valor\", \"taxa\", \"entrega\", \"quanto\"]
        if any(k in text for k in faq_keywords):
            return self.faq_agent.handle(request)
        return self.intent_agent.handle(request)


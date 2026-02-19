from typing import Any, Dict, Optional
from ..base import AgentBase, FAQResult

class FaqAgent(AgentBase):
    \"\"\"Agent para responder dúvidas frequentes (horário, preço, taxa).\"\"\"

    def __init__(self, adapters: Optional[Dict[str, Any]] = None):
        self.adapters = adapters or {}

    def answer_question(self, request: Dict[str, Any]) -> FAQResult:
        text = request.get(\"text\", \"\").lower()
        if \"horário\" in text or \"horario\" in text or \"abertura\" in text:
            return FAQResult(\"Nosso horário de funcionamento é 10:00-22:00 (todos os dias).\", source=\"config\")
        if \"preço\" in text or \"valor\" in text or \"quanto\" in text:
            return FAQResult(\"Consulte o catálogo de produtos; preços variam por item.\", source=\"catalog\")
        if \"taxa\" in text or \"entrega\" in text:
            return FAQResult(\"A taxa de entrega depende do endereço; consulte no checkout.\", source=\"checkout\")
        return FAQResult(\"Não entendi a pergunta — posso encaminhar para um atendente humano.\", source=\"fallback\")

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        res = self.answer_question(request)
        return {\"answer\": res.answer, \"source\": res.source}


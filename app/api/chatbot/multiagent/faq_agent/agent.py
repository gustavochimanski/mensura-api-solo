from typing import Any, Dict, Optional
from ..base import AgentBase, FAQResult

class FaqAgent(AgentBase):
    \"\"\"Agent para responder dúvidas frequentes (horário, preço, taxa).\"\"\"

    def __init__(self, adapters: Optional[Dict[str, Any]] = None):
        self.adapters = adapters or {}

    def answer_question(self, request: Dict[str, Any]) -> FAQResult:
        text = request.get(\"text\", \"\").lower()
        if \"horário\" in text or \"horario\" in text or \"abertura\" in text:
            return FAQResult(\"Nosso horário de funcionamento é 10:00-22:00 (todos os dias).\", source=\"config\")\n+        if \"preço\" in text or \"valor\" in text or \"quanto\" in text:\n+            return FAQResult(\"Consulte o catálogo de produtos; preços variam por item.\", source=\"catalog\")\n+        if \"taxa\" in text or \"entrega\" in text:\n+            return FAQResult(\"A taxa de entrega depende do endereço; consulte no checkout.\", source=\"checkout\")\n+        return FAQResult(\"Não entendi a pergunta — posso encaminhar para um atendente humano.\", source=\"fallback\")\n+\n+    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:\n+        res = self.answer_question(request)\n+        return {\"answer\": res.answer, \"source\": res.source}\n+\n*** End Patch

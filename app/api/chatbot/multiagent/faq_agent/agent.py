from typing import Any, Dict, Optional
from ..base import AgentBase, FAQResult
from ..adapters import MultiAgentAdapters

class FaqAgent(AgentBase):
    """Agente para responder dúvidas frequentes (horário, preço, taxa)."""

    def __init__(self, adapters: Optional[MultiAgentAdapters] = None):
        self.adapters = adapters or MultiAgentAdapters()

    def answer_question(self, request: Dict[str, Any]) -> FAQResult:
        text = request.get("text", "").lower()
        # horário / abertura
        if "horário" in text or "horario" in text or "abertura" in text:
            cfg = self.adapters.get_config()
            hours = cfg.get("operating_hours") or "10:00-22:00 (todos os dias)"
            return FAQResult(f"Nosso horário de funcionamento é {hours}.", source="config")
        # preço / valor
        if "preço" in text or "preco" in text or "valor" in text or "quanto" in text:
            # tentamos extrair um identificador simples do texto (fallback)
            # exemplo: "quanto custa X123"
            parts = text.split()
            product_id = next((p for p in parts if p.isalnum() and len(p) > 2), None)
            price = None
            if product_id:
                price = self.adapters.get_product_price(product_id)
            if price is not None:
                return FAQResult(f"O preço do produto ({product_id}) é R$ {price:.2f}.", source="catalog")
            return FAQResult("Consulte o catálogo de produtos; preços variam por item.", source="catalog")
        # taxa / entrega
        if "taxa" in text or "entrega" in text:
            # se tivermos adaptador de checkout, poderíamos calcular
            fee = self.adapters.get_delivery_fee({"raw_text": text})
            if fee is not None:
                return FAQResult(f"A taxa de entrega estimada é R$ {fee:.2f}.", source="checkout")
            return FAQResult("A taxa de entrega depende do endereço; consulte no checkout.", source="checkout")
        return FAQResult("Não entendi a pergunta — posso encaminhar para um atendente humano.", source="fallback")

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        res = self.answer_question(request)
        return {"answer": res.answer, "source": res.source}


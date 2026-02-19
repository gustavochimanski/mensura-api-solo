"""Adaptadores para reutilizar configurações e serviços existentes (legacy)."""
from typing import Any, Dict, Optional


class MultiAgentAdapters:
    """Wrapper que expõe APIs mínimas usadas pelos agentes e reaproveita o código legacy quando disponível."""

    def __init__(self) -> None:
        # tentar importar módulo de configuração do WhatsApp (compat shim)
        try:
            from app.api.chatbot.core import config_whatsapp  # type: ignore
            self._config = config_whatsapp
        except Exception:
            self._config = None

        # Produto/serviço legacy não está mais presente; deixamos _produto como None.
        self._produto = None

    def get_config(self) -> Dict[str, Any]:
        if self._config is None:
            return {}
        # expor apenas elementos seguros/necessários
        return {
            "d360_base_url": getattr(self._config, "D360_BASE_URL", None),
            "d360_api_key": getattr(self._config, "D360_API_KEY", None),
        }

    def get_product_price(self, product_identifier: str) -> Optional[float]:
        """Tenta obter preço do produto via código legacy (se disponível)."""
        if not self._produto:
            return None
        # função legacy pode ter outro nome; proteger com hasattr
        if hasattr(self._produto, "get_price_by_identifier"):
            try:
                return float(self._produto.get_price_by_identifier(product_identifier))
            except Exception:
                return None
        return None

    def get_delivery_fee(self, address: Dict[str, Any]) -> Optional[float]:
        # Placeholder: a implementação real pode chamar checkout gateway legacy
        return None


def get_adapters() -> MultiAgentAdapters:
    return MultiAgentAdapters()


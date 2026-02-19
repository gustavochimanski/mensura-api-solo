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

    # ----- helpers para fluxo de ver cardápio / cadastro rápido -----
    def handle_view_menu_flow(self, db, phone_number: str, text: str, empresa_id: int = 1) -> Dict[str, Any]:
        """When user asks for menu: if registered -> return menu link;
        otherwise create a quick customer (best-effort) and return the link.
        Returns a dict describing action to be taken by caller (e.g., send message).
        """
        # Detect intenção explicitamente
        intent = self.intent_agent.handle_intent({"text": text})
        if intent.intent != "ver_cardapio" and intent.intent != "create_order":
            return {"ok": False, "reason": "no_menu_intent"}

        # normalize phone and check existing customer
        try:
            from app.api.cadastros.services.service_cliente import ClienteService
            from app.api.chatbot.legacy.services import CustomerService
            from sqlalchemy import text as sql_text
        except Exception:
            # dependencies missing - abort gracefully
            return {"ok": False, "reason": "missing_dependencies"}

        cliente_svc = ClienteService(db)
        cliente = cliente_svc.repo.get_by_telefone(phone_number)

        if not cliente:
            # criar cadastro rápido com heurística de nome
            name_guess = None
            parts = (text or "").split()
            # pega primeira palavra com >2 caracteres como possível nome
            for p in parts:
                if p.isalpha() and len(p) > 2:
                    name_guess = p
                    break
            if not name_guess:
                # fallback para sufixo do telefone
                phone_clean = ''.join(ch for ch in phone_number if ch.isdigit())
                name_guess = f"Cliente {phone_clean[-4:]}" if phone_clean else "Cliente WhatsApp"

            customer_creator = CustomerService(db)
            try:
                created = customer_creator.cadastrar_rapido(name_guess, phone_number)
                cliente = created
            except Exception:
                # se falhar, continuamos sem cliente (fallback)
                cliente = None

        # busca link do cardápio da empresa
        cardapio_link = None
        try:
            q = sql_text("""SELECT cardapio_link FROM cadastros.empresas WHERE id = :empresa_id LIMIT 1""")
            r = db.execute(q, {"empresa_id": int(empresa_id)}).fetchone()
            if r and r[0]:
                cardapio_link = r[0]
        except Exception:
            cardapio_link = None

        # fallback para variável global/link padrão
        if not cardapio_link:
            try:
                from app.api.chatbot.legacy.core.utils.config_loader import LINK_CARDAPIO
                cardapio_link = LINK_CARDAPIO
            except Exception:
                cardapio_link = "https://chatbot.mensuraapi.com.br"

        return {"ok": True, "action": "send_menu_link", "link": cardapio_link, "cliente_id": getattr(cliente, "id", None)}

    def register_intent_agent(self, agent: IntentAgent) -> None:
        """Substitui o agente de intenção (útil para testes ou hot-swap)."""
        self.intent_agent = agent

    def register_faq_agent(self, agent: FaqAgent) -> None:
        """Substitui o agente de FAQ."""
        self.faq_agent = agent


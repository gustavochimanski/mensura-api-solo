"""
Carregamento de configurações do chatbot
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

# Link do cardápio (configurável)
LINK_CARDAPIO = "https://chatbot.mensuraapi.com.br"


class ConfigLoader:
    """
    Classe para carregar e gerenciar configurações do chatbot
    """

    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self._config_cache = None
        self._load_chatbot_config()

    def _load_chatbot_config(self):
        """Carrega configurações do chatbot para a empresa"""
        try:
            from app.api.chatbot.repositories.repo_chatbot_config import ChatbotConfigRepository
            repo = ChatbotConfigRepository(self.db)
            config = repo.get_by_empresa_id(self.empresa_id)
            self._config_cache = config
            if config:
                print(f"✅ Configuração do chatbot carregada: {config.nome} (aceita_pedidos={config.aceita_pedidos_whatsapp})")
        except Exception as e:
            print(f"⚠️ Erro ao carregar configuração do chatbot: {e}")
            self._config_cache = None

    def get_chatbot_config(self):
        """Retorna configuração do chatbot (com cache)"""
        return self._config_cache

    def obter_link_cardapio(self) -> str:
        """Obtém o link do cardápio da empresa"""
        try:
            empresa_query = text("""
                SELECT cardapio_link
                FROM cadastros.empresas
                WHERE id = :empresa_id
            """)
            result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
            empresa = result.fetchone()
            return empresa[0] if empresa and empresa[0] else LINK_CARDAPIO
        except Exception as e:
            print(f"⚠️ Erro ao buscar link do cardápio: {e}")
            return LINK_CARDAPIO

    def obter_mensagem_final_pedido(self) -> str:
        """
        Retorna a mensagem final apropriada baseada em aceita_pedidos_whatsapp.
        Se aceita pedidos: "Quer adicionar ao pedido? 😊"
        Se não aceita: mensagem com link do cardápio
        """
        config = self.get_chatbot_config()
        if config and not config.aceita_pedidos_whatsapp:
            link_cardapio = self.obter_link_cardapio()
            if config.mensagem_redirecionamento:
                mensagem = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
            else:
                mensagem = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
            return mensagem
        else:
            return "Quer adicionar ao pedido? 😊"

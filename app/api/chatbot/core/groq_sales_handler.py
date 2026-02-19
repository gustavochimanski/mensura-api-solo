"""
Handler de vendas integrado com Groq API (LLaMA 3.1 rápido e gratuito)
Inclui fluxo de endereços com Google Maps e endereços salvos
"""
import os
import httpx
import json
import re
import time
import unicodedata
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, text, or_, func
from datetime import datetime
from difflib import SequenceMatcher, get_close_matches

from .sales_prompts import SALES_SYSTEM_PROMPT
from .address_service import ChatbotAddressService
from .ingredientes_service import (
    IngredientesService,
    detectar_remocao_ingrediente,
    detectar_adicao_extra,
    detectar_pergunta_ingredientes
)
from .intention_agents import IntentionRouter
from .domain.produto_service import ProdutoDomainService
from .domain.carrinho_service import CarrinhoDomainService
from .domain.pagamento_service import PagamentoDomainService
from .application.conversacao_service import ConversacaoService
from .infrastructure.pagamento_repository import PagamentoRepository
from .utils.config_loader import ConfigLoader
from .utils.mensagem_formatters import MensagemFormatters
from .llm_policy import (
    build_system_prompt,
    clamp_temperature,
    extract_first_json_object,
    make_json_repair_prompt,
    validate_action_json,
)
from app.api.chatbot.services.service_carrinho import CarrinhoService
from app.api.chatbot.schemas.schema_carrinho import (
    AdicionarItemCarrinhoRequest,
    AtualizarItemCarrinhoRequest,
    RemoverItemCarrinhoRequest,
    ItemCarrinhoRequest,
    ReceitaCarrinhoRequest,
    ComboCarrinhoRequest,
)
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
from app.api.catalogo.adapters.receitas_adapter import ReceitasAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.services.service_busca_global import BuscaGlobalService
from .observability import ChatbotObservability

# Configuração do Groq - API Key deve ser configurada via variável de ambiente
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"  # Modelo menor = mais limite no free tier
DEFAULT_PROMPT_KEY = "atendimento-pedido-whatsapp"

# Link do cardápio (configurável)
LINK_CARDAPIO = "https://chatbot.mensuraapi.com.br"

# Definição das funções que a IA pode chamar (Function Calling)
AI_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "adicionar_produto",
            "description": "Adiciona um produto ao carrinho. Use APENAS quando o cliente especifica um PRODUTO do cardápio. Exemplos: 'me ve uma coca', 'quero 2 pizzas', 'manda um x-bacon', 'quero um x bacon sem tomate' (use adicionar_produto mesmo com personalização - o sistema aplica automaticamente). NÃO use para: 'fazer novo pedido', 'novo pedido', 'quero fazer pedido' (sem produto) - nesses casos use 'iniciar_novo_pedido'. NÃO use para frases genéricas como 'quero pedir' (sem produto) - nesses casos use 'iniciar_novo_pedido' ou 'conversar'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_busca": {
                        "type": "string",
                        "description": "Nome do produto que o cliente quer"
                    },
                    "quantidade": {
                        "type": "integer",
                        "description": "Quantidade desejada (padrão 1)",
                        "default": 1
                    }
                },
                "required": ["produto_busca"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalizar_pedido",
            "description": "Cliente quer FINALIZAR/FECHAR o pedido. Use quando: 'só isso', 'pode fechar', 'é isso', 'não quero mais nada', 'finalizar', 'fechar pedido', 'pronto', 'acabou'",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_cardapio",
            "description": "Cliente quer ver o CARDÁPIO COMPLETO. Use APENAS quando pedir explicitamente: 'mostra o cardápio', 'quero ver o menu', 'lista de produtos'. NÃO use para perguntas vagas como 'o que tem?'",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_carrinho",
            "description": "Cliente quer ver o carrinho/pedido atual. Exemplos: 'o que eu pedi?', 'ver meu pedido', 'quanto tá?', 'meu carrinho', 'quanto deu?'",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remover_produto",
            "description": "Cliente quer REMOVER algo do carrinho. Exemplos: 'tira a coca', 'remove o hamburguer', 'não quero mais a pizza', 'cancela a bebida'",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_busca": {
                        "type": "string",
                        "description": "Nome do produto a remover"
                    }
                },
                "required": ["produto_busca"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "informar_sobre_produto",
            "description": "Cliente quer SABER MAIS sobre um PRODUTO ESPECÍFICO mencionado na mensagem. Use quando a pergunta menciona um produto concreto. Exemplos: 'o que vem no x-bacon?', 'o que tem no x-bacon?', 'ingredientes da pizza', 'qual o tamanho da pizza?', 'tem lactose no hamburguer?', 'o que tem na calabresa?', 'quanto fica a coca cola?', 'quanto custa a pizza?', 'qual o preço do hamburguer?', 'quanto fica a coca cola 350ml?'. IMPORTANTE: Perguntas sobre PREÇO sempre usam esta função, NÃO use 'adicionar_produto'. NÃO use para perguntas genéricas como 'o que tem?' sem mencionar produto específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_busca": {
                        "type": "string",
                        "description": "Nome do produto específico que o cliente quer saber mais (ex: 'x-bacon', 'pizza calabresa', 'hamburguer')"
                    },
                    "pergunta": {
                        "type": "string",
                        "description": "O que o cliente quer saber (ingredientes, tamanho, etc) - opcional"
                    }
                },
                "required": ["produto_busca"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "personalizar_produto",
            "description": "Cliente quer PERSONALIZAR um produto JÁ ADICIONADO removendo ingrediente ou adicionando extra. Use APENAS quando NÃO há produto novo na mensagem. Exemplos: 'sem cebola' (personaliza último produto), 'tira o tomate' (personaliza último produto), 'com queijo extra' (personaliza último produto). IMPORTANTE: Se a mensagem tem produto + personalização (ex: 'quero x bacon sem tomate'), use 'adicionar_produto' em vez de 'personalizar_produto'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_busca": {
                        "type": "string",
                        "description": "Nome do produto a personalizar (pode ser vazio se for o último adicionado)"
                    },
                    "acao": {
                        "type": "string",
                        "enum": ["remover_ingrediente", "adicionar_extra"],
                        "description": "Tipo de personalização"
                    },
                    "item": {
                        "type": "string",
                        "description": "Nome do ingrediente a remover ou adicional a incluir"
                    }
                },
                "required": ["acao", "item"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_adicionais",
            "description": "Cliente quer ver os ADICIONAIS disponíveis para um produto. Exemplos: 'quais adicionais tem?', 'posso colocar mais alguma coisa?', 'tem extra de queijo?', 'quais bordas tem?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_busca": {
                        "type": "string",
                        "description": "Nome do produto para ver adicionais (pode ser vazio se for o último adicionado)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "conversar",
            "description": "Para QUALQUER conversa casual, saudações, perguntas vagas ou quando não souber o que fazer. Exemplos: 'oi', 'eae', 'tudo bem?', 'o que eu quero?', 'não sei', 'hum', 'que que tem ai de bom?', 'me ajuda', 'sugestão'",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_conversa": {
                        "type": "string",
                        "enum": ["saudacao", "pergunta_vaga", "pedido_sugestao", "duvida_geral", "resposta_generica"],
                        "description": "Tipo de conversa detectada"
                    },
                    "contexto": {
                        "type": "string",
                        "description": "Contexto adicional da conversa"
                    }
                },
                "required": ["tipo_conversa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_combos",
            "description": "Cliente quer ver os COMBOS disponíveis. Exemplos: 'tem combo?', 'quais combos tem?', 'mostra os combos', 'promoção', 'combo família', 'combos', 'tem promoção?'",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_taxa_entrega",
            "description": "Cliente quer saber o VALOR DA TAXA DE ENTREGA/FRETE para um endereço. Use quando perguntar sobre: 'qual a taxa de entrega?', 'quanto é o frete?', 'qual o valor da entrega?', 'quanto custa a entrega?', 'qual a taxa para [endereço]?', 'quanto fica a entrega para [endereço]?', 'fala pra mi quanto que fica pra entregar aqui na rua X'. IMPORTANTE: Esta é uma PERGUNTA sobre taxa de entrega, NÃO é pedido de produto! Se a mensagem contém um endereço, passe a mensagem completa em mensagem_original para extração automática.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endereco": {
                        "type": "string",
                        "description": "Endereço mencionado pelo cliente (opcional, pode ser vazio se não mencionou endereço específico)"
                    },
                    "mensagem_original": {
                        "type": "string",
                        "description": "Mensagem original do cliente completa (use quando o endereço está na mensagem mas não está claro, ex: 'fala pra mi quanto que fica pra entregar aqui na rua calendulas 140')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "informar_sobre_estabelecimento",
            "description": "Cliente quer saber informações sobre o estabelecimento, como horário de funcionamento, localização, onde fica. Use quando perguntar: 'qual o horário?', 'que horas vocês abrem?', 'até que horas?', 'onde vocês ficam?', 'onde fica?', 'qual o endereço?', 'onde está localizado?', 'qual a localização?', 'horário de funcionamento', 'horário de trabalho'",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_pergunta": {
                        "type": "string",
                        "enum": ["horario", "localizacao", "ambos"],
                        "description": "Tipo de informação solicitada: horario (horário de funcionamento), localizacao (onde fica), ambos (horário e localização)"
                    }
                },
                "required": ["tipo_pergunta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "chamar_atendente",
            "description": "Cliente quer falar com um atendente humano. Use quando o cliente pedir explicitamente: 'chamar atendente', 'quero falar com alguém', 'preciso de um humano', 'atendente humano', 'quero atendimento humano', 'falar com atendente', 'ligar atendente', 'chama alguém para mim'",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "iniciar_novo_pedido",
            "description": "Cliente quer INICIAR/COMEÇAR um NOVO pedido do zero, limpando o carrinho atual. Use quando o cliente disser: 'fazer novo pedido', 'novo pedido', 'começar de novo', 'comecar de novo', 'iniciar novo pedido', 'quero fazer pedido', 'quero pedir' (quando não menciona produto específico). IMPORTANTE: NÃO use para quando o cliente menciona um produto específico (ex: 'quero fazer pedido de pizza' → use adicionar_produto).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Prompt para a IA interpretar intenções - VERSÃO CONVERSACIONAL
AI_INTERPRETER_PROMPT = """Você é um atendente HUMANO de delivery via WhatsApp. Seja natural e simpático!

REGRA DE OURO: Na dúvida, use "conversar". É melhor conversar do que fazer ação errada!

=== QUANDO USAR CADA FUNÇÃO ===

✅ adicionar_produto - APENAS quando cliente PEDE CLARAMENTE um produto:
   - "me ve uma coca" → adicionar_produto(produto_busca="coca")
   - "quero pizza calabresa" → adicionar_produto(produto_busca="pizza calabresa")
   - "2 x-bacon" → adicionar_produto(produto_busca="x-bacon", quantidade=2)
   - "quero um x bacon sem tomate" → adicionar_produto(produto_busca="x bacon") (o sistema aplica "sem tomate" automaticamente)
   - "me ve uma pizza sem cebola" → adicionar_produto(produto_busca="pizza") (o sistema aplica "sem cebola" automaticamente)

❌ NÃO use adicionar_produto para:
   - "fazer novo pedido" → use iniciar_novo_pedido
   - "novo pedido" → use iniciar_novo_pedido
   - "quero fazer pedido" (sem produto) → use iniciar_novo_pedido
   - "quero pedir" (sem produto) → use iniciar_novo_pedido
   - "o que tem?" → use conversar
   - "tem coca?" → use informar_sobre_produto (é pergunta, não pedido)
   - "quanto fica a coca?" → use informar_sobre_produto (é pergunta de PREÇO, não pedido)
   - "quanto custa a pizza?" → use informar_sobre_produto (é pergunta de PREÇO, não pedido)
   - "que que é isso?" → use conversar

✅ conversar - Para TUDO que não for ação clara:
   - Saudações: "oi", "eae", "opa", "tudo bem?" → conversar(tipo="saudacao")
   - Perguntas vagas: "o que tem?", "que que é bom?" → conversar(tipo="pergunta_vaga")
   - Pedido sugestão: "me indica algo", "o que você recomenda?" → conversar(tipo="pedido_sugestao")
   - Dúvidas: "vocês entregam?", "até que horas?" → conversar(tipo="duvida_geral")
   - Respostas sem sentido: "hum", "talvez", "não sei" → conversar(tipo="resposta_generica")

✅ informar_sobre_produto - Quando quer SABER sobre produto (não pedir):
   - "o que vem no x-bacon?" → informar_sobre_produto(produto_busca="x-bacon")
   - "a pizza é grande?" → informar_sobre_produto(produto_busca="pizza")
   - "tem lactose?" → informar_sobre_produto
   - "quanto fica a coca cola?" → informar_sobre_produto(produto_busca="coca cola") ⚠️ PERGUNTA DE PREÇO!
   - "quanto custa a pizza?" → informar_sobre_produto(produto_busca="pizza") ⚠️ PERGUNTA DE PREÇO!
   - "qual o preço do hamburguer?" → informar_sobre_produto(produto_busca="hamburguer") ⚠️ PERGUNTA DE PREÇO!
   - "quanto fica a coca cola 350ml?" → informar_sobre_produto(produto_busca="coca cola 350ml") ⚠️ PERGUNTA DE PREÇO!

✅ ver_cardapio - APENAS quando pede EXPLICITAMENTE o cardápio:
   - "mostra o cardápio" → ver_cardapio
   - "quero ver o menu" → ver_cardapio
   ❌ NÃO use para: "o que tem?", "tem o que ai?" (use conversar)

✅ finalizar_pedido - Quando quer FECHAR o pedido:
   - "só isso", "pode fechar", "é isso", "pronto", "não quero mais nada"

✅ ver_carrinho - Quando quer ver O QUE JÁ PEDIU:
   - "o que eu pedi?", "quanto tá?", "meu pedido"

✅ remover_produto - Quando quer TIRAR algo do carrinho:
   - "tira a coca", "remove a pizza", "não quero mais o hamburguer"

✅ personalizar_produto - Quando quer CUSTOMIZAR um produto JÁ ADICIONADO (tirar ingrediente ou adicionar extra):
   - "sem cebola" → personalizar_produto(acao="remover_ingrediente", item="cebola") (personaliza último produto)
   - "tira o tomate" → personalizar_produto(acao="remover_ingrediente", item="tomate") (personaliza último produto)
   - "com queijo extra" → personalizar_produto(acao="adicionar_extra", item="queijo extra") (personaliza último produto)
   - "adiciona bacon" → personalizar_produto(acao="adicionar_extra", item="bacon") (personaliza último produto)
   ⚠️ IMPORTANTE: Se a mensagem tem PRODUTO + personalização (ex: "quero x bacon sem tomate"), use "adicionar_produto" em vez de "personalizar_produto"!

✅ ver_adicionais - Quando quer ver os EXTRAS disponíveis:
   - "quais adicionais tem?" → ver_adicionais
   - "tem borda recheada?" → ver_adicionais
   - "posso colocar mais queijo?" → ver_adicionais

✅ ver_combos - Quando quer ver os COMBOS/PROMOÇÕES disponíveis:
   - "tem combo?" → ver_combos
   - "quais combos tem?" → ver_combos
   - "mostra os combos" → ver_combos
   - "tem promoção?" → ver_combos
   - "combo família" → ver_combos
   - "combos" → ver_combos

✅ calcular_taxa_entrega - Quando quer saber o VALOR DA TAXA DE ENTREGA/FRETE:
   - "qual a taxa de entrega?" → calcular_taxa_entrega()
   - "quanto é o frete?" → calcular_taxa_entrega()
   - "qual o valor da entrega?" → calcular_taxa_entrega()
   - "quanto custa a entrega?" → calcular_taxa_entrega()
   - "qual a taxa para rua xyz?" → calcular_taxa_entrega(endereco="rua xyz")
   - "quanto fica a entrega para [endereço]?" → calcular_taxa_entrega(endereco="[endereço]")
   - "fala pra mi quanto que fica pra entregar aqui na rua calendulas 140" → calcular_taxa_entrega(mensagem_original="fala pra mi quanto que fica pra entregar aqui na rua calendulas 140")
   ⚠️ IMPORTANTE: Perguntas sobre TAXA DE ENTREGA sempre usam esta função, NÃO use 'adicionar_produto' ou 'informar_sobre_produto'! Se o endereço está na mensagem mas não está claro, use mensagem_original.

✅ chamar_atendente - Quando o cliente quer falar com um atendente humano:
   - "chamar atendente" → chamar_atendente()
   - "quero falar com alguém" → chamar_atendente()
   - "preciso de um humano" → chamar_atendente()
   - "atendente humano" → chamar_atendente()
   - "quero atendimento humano" → chamar_atendente()
   - "falar com atendente" → chamar_atendente()
   - "ligar atendente" → chamar_atendente()
   - "chama alguém para mim" → chamar_atendente()

✅ iniciar_novo_pedido - Quando o cliente quer INICIAR um NOVO pedido do zero:
   - "fazer novo pedido" → iniciar_novo_pedido()
   - "novo pedido" → iniciar_novo_pedido()
   - "começar de novo" → iniciar_novo_pedido()
   - "quero fazer pedido" → iniciar_novo_pedido() (quando NÃO menciona produto)
   - "quero pedir" → iniciar_novo_pedido() (quando NÃO menciona produto)
   ⚠️ IMPORTANTE: Se menciona produto específico (ex: "quero fazer pedido de pizza"), use "adicionar_produto" em vez de "iniciar_novo_pedido"!

❌ NÃO use adicionar_produto para:
   - "fazer novo pedido" → use iniciar_novo_pedido
   - "quero fazer pedido" (sem produto) → use iniciar_novo_pedido
   - "quero pedir" (sem produto) → use iniciar_novo_pedido

=== PRODUTOS DISPONÍVEIS ===
{produtos_lista}

=== CARRINHO ATUAL ===
{carrinho_atual}

Analise a mensagem e escolha a função correta. NA DÚVIDA, USE "conversar"!"""

# Estados da conversa
STATE_WELCOME = "welcome"
STATE_CONVERSANDO = "conversando"  # NOVO: IA conversacional livre
STATE_AGUARDANDO_PEDIDO = "aguardando_pedido"
STATE_AGUARDANDO_QUANTIDADE = "aguardando_quantidade"
STATE_AGUARDANDO_MAIS_ITENS = "aguardando_mais_itens"
STATE_PERGUNTANDO_ENTREGA_RETIRADA = "perguntando_entrega_retirada"  # NOVO: Entrega ou retirada?
STATE_VERIFICANDO_ENDERECO = "verificando_endereco"
STATE_LISTANDO_ENDERECOS = "listando_enderecos"
STATE_BUSCANDO_ENDERECO_GOOGLE = "buscando_endereco_google"
STATE_SELECIONANDO_ENDERECO_GOOGLE = "selecionando_endereco_google"
STATE_COLETANDO_COMPLEMENTO = "coletando_complemento"
STATE_COLETANDO_PAGAMENTO = "coletando_pagamento"
STATE_CONFIRMANDO_PEDIDO = "confirmando_pedido"
# Estado para cadastro rápido de cliente (durante pedido)
STATE_CADASTRO_NOME = "cadastro_nome"


class GroqSalesHandler:
    """
    Handler de vendas usando Groq API com LLaMA 3.1
    Busca dados do banco e gera respostas naturais
    Integra fluxo de endereços com Google Maps
    """

    def __init__(self, db: Session, empresa_id: int = 1, emit_welcome_message: bool = True, prompt_key: str = DEFAULT_PROMPT_KEY):
        self.db = db
        self.empresa_id = empresa_id
        self.prompt_key = prompt_key
        self.produto_service = ProdutoDomainService(db, empresa_id)
        self.config_loader = ConfigLoader(db, empresa_id)
        self.formatters = MensagemFormatters(db, empresa_id)
        # Quando True, o handler pode responder com a mensagem longa de boas-vindas.
        # No WhatsApp, preferimos enviar a boas-vindas com botões no router.py (mensagem interativa).
        self.emit_welcome_message = emit_welcome_message
        self.address_service = ChatbotAddressService(db, empresa_id)
        self.ingredientes_service = IngredientesService(db, empresa_id)
        self.carrinho_domain = CarrinhoDomainService(db, empresa_id, self.ingredientes_service)
        self.conversacao_service = ConversacaoService(self.db, empresa_id=self.empresa_id, prompt_key=self.prompt_key)
        self.pagamento_repo = PagamentoRepository(self.db)
        self.pagamento_domain = PagamentoDomainService(empresa_id=self.empresa_id)
        # Carrega configurações do chatbot
        self._config_cache = None
        self._carrinho_service = None
        # Router de intenções com múltiplos agentes especializados
        self.intention_router = IntentionRouter()
        # FASE 4: Observabilidade (inicializado por user_id quando disponível)
        self.observability: Optional[ChatbotObservability] = None
        self._load_chatbot_config()

    def _buscar_meios_pagamento(self) -> List[Dict]:
        """Busca meios de pagamento ativos do banco (delegado para `PagamentoRepository`)."""
        return self.pagamento_repo.buscar_meios_pagamento_ativos()

    def _buscar_empresas_ativas(self) -> List[Dict]:
        """
        Busca todas as empresas ativas do banco de dados.
        Retorna lista de dicionários com informações das empresas.
        """
        return self.formatters.buscar_empresas_ativas()

    def _formatar_horarios_funcionamento(self, horarios_funcionamento) -> str:
        """
        Formata os horários de funcionamento em texto legível.
        horarios_funcionamento é um JSONB com estrutura:
        [{"dia_semana": 0..6, "intervalos": [{"inicio":"HH:MM","fim":"HH:MM"}]}]
        """
        return self.formatters.formatar_horarios_funcionamento(horarios_funcionamento)

    def _formatar_localizacao_empresas(self, empresas: List[Dict], empresa_atual_id: int) -> str:
        """
        Formata informações de localização das empresas.
        Se houver apenas 1 empresa, retorna informações dela.
        Se houver mais de 1, retorna informações da atual + lista das outras.
        """
        return self.formatters.formatar_localizacao_empresas(empresas, empresa_atual_id)

    def _normalizar_mensagem(self, mensagem: str) -> str:
        """
        Normaliza a mensagem para regras simples:
        - remove acentos
        - troca pontuação por espaço
        - colapsa espaços
        """
        msg = (mensagem or "").lower().strip()
        msg = msg.replace("´", "'").replace("`", "'").replace("’", "'").replace("‘", "'")
        msg = unicodedata.normalize("NFKD", msg)
        msg = "".join(ch for ch in msg if not unicodedata.combining(ch))
        msg = re.sub(r"[^a-z0-9\s]", " ", msg)
        msg = re.sub(r"\s+", " ", msg).strip()
        return msg

    async def should_send_order_summary(self, message_text: str, pedido_aberto_info: dict, phone_number: str | None = None) -> str | None:
        """
        Decide se, dada uma mensagem do cliente, devemos retornar o resumo
        do pedido em aberto. Retorna a mensagem pronta se deve enviar, ou None.

        A decisão é feita por heurística simples (normalização + substrings).
        O orquestrador (router) deve chamar esta função e, se receber uma string,
        enviar via WhatsApp e registrar o histórico.
        """
        try:
            if not pedido_aberto_info:
                return None

            msg = (message_text or "").strip()
            if not msg:
                return None

            norm = self._normalizar_mensagem(msg)
            ativadores = ["atualiz", "tualiz", "acompanhar", "status", "acompanhar pedido", "receber atualiz"]
            if not any(a in norm for a in ativadores):
                return None

            # Monta a mensagem resumo (formato compacto)
            status = pedido_aberto_info.get('status', '')
            numero_pedido = pedido_aberto_info.get('numero_pedido', 'N/A')
            tipo_entrega = pedido_aberto_info.get('tipo_entrega', '')
            created_at = pedido_aberto_info.get('created_at')
            itens = pedido_aberto_info.get('itens', [])
            subtotal = pedido_aberto_info.get('subtotal', 0.0)
            taxa_entrega = pedido_aberto_info.get('taxa_entrega', 0.0)
            desconto = pedido_aberto_info.get('desconto', 0.0)
            valor_total = pedido_aberto_info.get('valor_total', 0.0)
            endereco = pedido_aberto_info.get('endereco')
            meio_pagamento = pedido_aberto_info.get('meio_pagamento')
            mesa_codigo = pedido_aberto_info.get('mesa_codigo')

            status_texto = {
                'P': 'Pendente',
                'I': 'Em impressão',
                'R': 'Em preparo',
                'S': 'Saiu para entrega',
                'A': 'Aguardando pagamento',
                'D': 'Editado',
                'X': 'Em edição'
            }.get(status, status)

            tipo_entrega_texto = {
                'DELIVERY': 'Delivery',
                'RETIRADA': 'Retirada',
                'BALCAO': 'Balcão',
                'MESA': 'Mesa'
            }.get(tipo_entrega, tipo_entrega)

            data_formatada = ""
            if created_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    data_formatada = created_at

            mensagem_pedido = f"📦 *Pedido #{numero_pedido}* | {status_texto} | {tipo_entrega_texto}"
            if mesa_codigo:
                mensagem_pedido += f" | Mesa: {mesa_codigo}"
            if data_formatada:
                mensagem_pedido += f"\n📅 {data_formatada}"
            mensagem_pedido += "\n\n*Itens:*\n"
            if itens:
                for item in itens:
                    nome = item.get('nome', 'Item')
                    qtd = item.get('quantidade', 1)
                    preco_total_item = item.get('preco_total', 0.0)
                    mensagem_pedido += f"• {qtd}x {nome} - R$ {preco_total_item:.2f}\n"
            else:
                mensagem_pedido += "Nenhum item encontrado\n"

            mensagem_pedido += f"\n*Resumo:* Subtotal: R$ {subtotal:.2f}"
            if taxa_entrega > 0:
                mensagem_pedido += f" | Entrega: R$ {taxa_entrega:.2f}"
            if desconto > 0:
                mensagem_pedido += f" | Desconto: -R$ {desconto:.2f}"
            mensagem_pedido += f"\n*TOTAL: R$ {valor_total:.2f}*"

            if endereco:
                mensagem_pedido += "\n\n📍 *Entrega:*"
                end_parts = []
                if endereco.get('rua'):
                    end_parts.append(endereco['rua'])
                if endereco.get('numero'):
                    end_parts.append(endereco['numero'])
                if end_parts:
                    mensagem_pedido += f"\n{', '.join(end_parts)}"
                endereco_line = []
                if endereco.get('complemento'):
                    endereco_line.append(endereco['complemento'])
                if endereco.get('bairro'):
                    endereco_line.append(endereco['bairro'])
                if endereco_line:
                    mensagem_pedido += f"\n{', '.join(endereco_line)}"
                cidade_line = []
                if endereco.get('cidade'):
                    cidade_line.append(endereco['cidade'])
                if endereco.get('cep'):
                    cidade_line.append(f"CEP: {endereco['cep']}")
                if cidade_line:
                    mensagem_pedido += f"\n{' - '.join(cidade_line)}"

            if meio_pagamento:
                mensagem_pedido += f"\n\n💳 *Pagamento:* {meio_pagamento}"

            mensagem_pedido += "\n\nComo posso te ajudar? 😊"

            return mensagem_pedido
        except Exception as e:
            # Em caso de erro, não bloquear o fluxo principal
            import logging
            logging.getLogger(__name__).error(f"[should_send_order_summary] Erro: {e}", exc_info=True)
            return None

    def _extrair_quantidade_pergunta(self, pergunta: str, nome_produto: str) -> int:
        """
        Extrai quantidade da pergunta quando o cliente pergunta preço com quantidade.
        Ex: "quanto fica 6 coca" -> 6
        """
        if not pergunta:
            return 1

        msg = self._normalizar_mensagem(pergunta)
        if not msg:
            return 1

        nome_norm = self._normalizar_mensagem(nome_produto)
        tokens = [t for t in nome_norm.split() if len(t) > 2]
        tokens = [t for t in tokens if not re.match(r'^\d+(ml|l)$', t)]
        if not tokens:
            tokens = nome_norm.split()

        for match in re.finditer(r'\b(\d+)\s*x?\s*([a-z][a-z0-9]*)', msg):
            qtd = int(match.group(1))
            palavra = match.group(2)
            if palavra in tokens:
                return max(qtd, 1)

        if any(t in msg for t in tokens):
            for match in re.finditer(r'\b(\d+)\b', msg):
                pos = match.end()
                if re.match(r'^\s*(ml|l)\b', msg[pos:]):
                    continue
                return max(int(match.group(1)), 1)

        return 1

    def _extrair_itens_pergunta_preco(self, mensagem: str) -> List[Dict[str, Any]]:
        """
        Extrai itens e quantidades em perguntas de preço com múltiplos produtos.
        Ex: "quanto fica 2 x bacon e 1 coca lata" -> [{"produto_busca": "x bacon", "quantidade": 2}, ...]
        """
        msg = self._normalizar_mensagem(mensagem)
        if not msg:
            return []

        match = re.search(
            r'(quanto\s+(?:que\s+)?(?:fica|custa|e|é)|qual\s+(?:o\s+)?(?:pre[cç]o|valor)|pre[cç]o|valor)',
            msg,
            re.IGNORECASE
        )
        if match:
            msg = msg[match.end():].strip()

        partes = re.split(r'\s+e\s+|,|;', msg)
        itens = []

        for parte in partes:
            trecho = parte.strip()
            if not trecho:
                continue

            qtd = 1
            produto = trecho
            prefer_alt = False
            produto_alt = ""

            m_qtd = re.match(r'^(\d+)\s*(x)?\s*(.+)$', trecho)
            if m_qtd:
                qtd = int(m_qtd.group(1))
                tem_x = bool(m_qtd.group(2))
                produto = m_qtd.group(3).strip()
                if tem_x and produto and not produto.startswith("x "):
                    produto_alt = f"x {produto}"
                    prefer_alt = True

            produto = re.sub(r'^(a|o|da|do|de)\s+', '', produto, flags=re.IGNORECASE).strip()
            if not produto:
                continue

            itens.append({
                "produto_busca": produto,
                "quantidade": max(qtd, 1),
                "produto_busca_alt": produto_alt,
                "prefer_alt": prefer_alt
            })

        return itens

    async def _extrair_endereco_com_ia(self, mensagem: str) -> str:
        """
        Extrai endereço de uma mensagem de forma heurística.
        Mantém o nome original por compatibilidade com chamadas existentes.
        """
        if not mensagem:
            return ""

        texto = re.sub(r"\s+", " ", mensagem).strip()
        if not texto:
            return ""

        texto_limpo = re.sub(
            r"^(voc[eê]s?\s+)?(entregam|entrega|fazem\s+entrega|faz\s+entrega|tem\s+entrega)\s*(na|no|em|para|pra)?\s*",
            "",
            texto,
            flags=re.IGNORECASE
        ).strip()

        def _limpar_fim(valor: str) -> str:
            return re.sub(r"[?!.,;:\s]+$", "", valor).strip()

        padrao_rua = r"(?:rua|r\.|avenida|av\.|travessa|tv\.|alameda|rodovia|estrada|pra[cç]a|loteamento|quadra|qd\.|q\.)"

        match_preposicao = re.search(
            rf"\b(?:na|no|em|para|pra)\s+({padrao_rua}\s+[^,;!?]+)",
            texto,
            flags=re.IGNORECASE
        )
        if match_preposicao:
            return _limpar_fim(match_preposicao.group(1))

        match_rua = re.search(
            rf"\b({padrao_rua}\s+[^,;!?]+)",
            texto_limpo,
            flags=re.IGNORECASE
        )
        if match_rua:
            return _limpar_fim(match_rua.group(1))

        # Fallback: usa o texto restante se parecer endereço (tem número ou CEP)
        if re.search(r"\d{3,}", texto_limpo):
            return _limpar_fim(texto_limpo)

        return ""

    def _extrair_itens_pedido(self, mensagem: str) -> List[Dict[str, Any]]:
        """
        Extrai itens e quantidades de pedidos com múltiplos produtos.
        Ex: "não, vou querer apenas 1 x bacon e 1 coca" -> [{"produto_busca": "x bacon", "quantidade": 1}, ...]
        """
        msg = self._normalizar_mensagem(mensagem)
        if not msg:
            return []

        # Remove negação inicial e frases comuns de pedido
        msg = re.sub(r'^(n[aã]o|nao)\s*,?\s*', '', msg, flags=re.IGNORECASE)
        msg = re.sub(
            r'^(vou\s+querer|quero|qro|gostaria\s+de|me\s+ve|me\s+v[eê]|manda|traz|adiciona|adicionar)\s+',
            '',
            msg,
            flags=re.IGNORECASE
        )
        msg = re.sub(r'^(apenas|so|só|somente)\s+', '', msg, flags=re.IGNORECASE)
        if not msg:
            return []

        partes = re.split(r'\s+e\s+|,|;|\s+mais\s+', msg)
        itens = []
        mapa_qtd = {
            'um': 1, 'uma': 1,
            'dois': 2, 'duas': 2,
            'tres': 3, 'três': 3,
            'quatro': 4, 'cinco': 5
        }

        for parte in partes:
            trecho = parte.strip()
            if not trecho:
                continue

            qtd = 1
            produto = trecho
            tem_x = False

            m_qtd = re.match(r'^(\d+)\s*(x)?\s*(.+)$', trecho)
            if m_qtd:
                qtd = int(m_qtd.group(1))
                tem_x = bool(m_qtd.group(2))
                produto = m_qtd.group(3).strip()
            else:
                m_qtd_txt = re.match(r'^(um|uma|dois|duas|tres|três|quatro|cinco)\s+(.+)$', trecho)
                if m_qtd_txt:
                    qtd = mapa_qtd.get(m_qtd_txt.group(1), 1)
                    produto = m_qtd_txt.group(2).strip()

            produto = re.sub(r'^(a|o|da|do|de)\s+', '', produto, flags=re.IGNORECASE).strip()
            produto = re.sub(r'\s+por\s+favor$', '', produto, flags=re.IGNORECASE).strip()
            if not produto:
                continue

            prefer_alt = False
            produto_alt = ""
            if tem_x and produto and not produto.startswith("x "):
                produto_alt = f"x {produto}"
                prefer_alt = True

            itens.append({
                "produto_busca": produto,
                "quantidade": max(qtd, 1),
                "produto_busca_alt": produto_alt,
                "prefer_alt": prefer_alt
            })

        return itens

    def _resolver_produto_para_preco(
        self,
        produto_busca: str,
        produto_busca_alt: str,
        prefer_alt: bool,
        produtos: List[Dict]
    ) -> Optional[Dict]:
        if prefer_alt and produto_busca_alt:
            produto = self._buscar_produto_por_termo(produto_busca_alt, produtos)
            if produto:
                return produto
        produto = self._buscar_produto_por_termo(produto_busca, produtos)
        if produto:
            return produto
        if produto_busca_alt:
            return self._buscar_produto_por_termo(produto_busca_alt, produtos)
        return None

    def _gerar_resposta_preco_itens(self, user_id: str, dados: Dict, itens: List[Dict[str, Any]], produtos: List[Dict]) -> str:
        encontrados = []
        faltando = []
        total = 0.0
        pendentes = []

        for item in itens:
            produto_busca = item.get("produto_busca", "")
            produto_busca_alt = item.get("produto_busca_alt", "")
            prefer_alt = bool(item.get("prefer_alt", False))
            quantidade = int(item.get("quantidade", 1) or 1)

            produto = self._resolver_produto_para_preco(
                produto_busca, produto_busca_alt, prefer_alt, produtos
            )
            if not produto:
                faltando.append(produto_busca or produto_busca_alt)
                continue

            subtotal = produto["preco"] * quantidade
            total += subtotal
            encontrados.append((quantidade, produto, subtotal))
            pendentes.append({
                "id": produto.get("id"),
                "tipo": produto.get("tipo"),
                "nome": produto.get("nome"),
                "preco": produto.get("preco"),
                "quantidade": quantidade
            })

        if not encontrados:
            dados.pop("pendente_adicao_itens", None)
            return "❌ Não encontrei esses itens no cardápio 😔\n\nQuer que eu mostre o que temos disponível? 😊"

        msg = "💰 *Valores:*\n"
        for quantidade, produto, subtotal in encontrados:
            if quantidade > 1:
                msg += f"• {quantidade}x {produto['nome']} - R$ {subtotal:.2f}\n"
            else:
                msg += f"• {produto['nome']} - R$ {produto['preco']:.2f}\n"

        carrinho_resp = self._obter_carrinho_db(user_id)
        total_atual = float(carrinho_resp.valor_total) if carrinho_resp and carrinho_resp.valor_total is not None else 0.0
        if total_atual > 0:
            msg += f"\nTotal atual do carrinho: R$ {total_atual:.2f}\n"
            msg += f"Total com esses itens: R$ {total_atual + total:.2f}\n\n"
        else:
            msg += f"\nTotal: R$ {total:.2f}\n\n"
        if faltando:
            msg += f"Obs: não encontrei {', '.join(faltando)} no cardápio.\n\n"

        dados["pendente_adicao_itens"] = pendentes
        msg += self._obter_mensagem_final_pedido()
        return msg

    def _detectar_forma_pagamento_em_mensagem(self, mensagem: str) -> Optional[Dict]:
        """
        Detecta se a mensagem contém uma forma de pagamento.
        Retorna o meio de pagamento encontrado ou None.
        Funciona em qualquer parte do fluxo!

        IMPORTANTE: Ignora mensagens que são PERGUNTAS sobre pagamento
        (ex: "aceitam pix?", "pode ser no cartão?")
        """
        msg = self._normalizar_mensagem(mensagem)

        # IGNORA se for uma PERGUNTA sobre pagamento (não uma seleção)
        palavras_pergunta = ['aceita', 'aceitam', 'pode ser', 'posso pagar', 'da pra', 'dá pra',
                            'tem como', 'consigo', 'vocês aceitam', 'voces aceitam', 'aceito']
        if any(p in msg for p in palavras_pergunta):
            print(f"💳 Ignorando detecção - mensagem é uma pergunta: {msg[:50]}")
            return None

        # IGNORA se termina com ? (é uma pergunta)
        if msg.endswith('?') or msg.endswith('/'):
            print(f"💳 Ignorando detecção - mensagem termina com ? ou /: {msg[:50]}")
            return None

        meios = self._buscar_meios_pagamento()

        # Patterns para cada tipo de pagamento - mais específicos
        patterns_por_tipo = {
            'PIX_ENTREGA': ['pagar pix', 'pago pix', 'no pix', 'pelo pix', 'via pix', 'por pix', 'fazer pix', 'vou pagar pix'],
            'PIX_ONLINE': ['pix online', 'pagar pix', 'pago pix'],
            'DINHEIRO': ['pagar dinheiro', 'pago dinheiro', 'em dinheiro', 'no dinheiro', 'especie', 'espécie',
                        'pagar na hora', 'cash', 'em maos', 'em mãos', 'vou pagar dinheiro'],
            'CARTAO_ENTREGA': ['pagar cartao', 'pagar cartão', 'pago cartao', 'pago cartão',
                              'no cartao', 'no cartão', 'pelo cartao', 'pelo cartão',
                              'no credito', 'no crédito', 'no debito', 'no débito',
                              'maquininha', 'na maquina', 'na máquina',
                              'passar cartao', 'passar cartão', 'vou pagar cartao', 'vou pagar cartão'],
            'OUTROS': []
        }

        # Primeiro verifica se a mensagem é APENAS o nome/tipo de pagamento (seleção direta)
        # Ex: "pix", "dinheiro", "cartão", "1", "2"
        palavras_pagamento_direto = ['pix', 'dinheiro', 'cartao', 'cartão', 'credito', 'crédito', 'debito', 'débito']
        msg_limpa = msg.replace(',', '').replace('.', '').strip()

        if msg_limpa in palavras_pagamento_direto:
            # Mensagem é APENAS a forma de pagamento
            for meio in meios:
                nome_lower = meio['nome'].lower()
                tipo = meio.get('tipo', 'OUTROS')

                if msg_limpa in nome_lower:
                    return meio
                if msg_limpa == 'pix' and 'PIX' in tipo:
                    return meio
                if msg_limpa in ['cartao', 'cartão', 'credito', 'crédito', 'debito', 'débito'] and tipo == 'CARTAO_ENTREGA':
                    return meio
                if msg_limpa == 'dinheiro' and tipo == 'DINHEIRO':
                    return meio

        # Depois verifica pelos patterns do tipo (frases mais completas)
        for meio in meios:
            tipo = meio.get('tipo', 'OUTROS')
            patterns = patterns_por_tipo.get(tipo, [])
            for pattern in patterns:
                if pattern in msg:
                    return meio

        return None

    def _interpretar_intencao_regras(
        self,
        mensagem: str,
        produtos: List[Dict],
        carrinho: List[Dict],
        dados: Optional[dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Interpretação de intenção usando múltiplos agentes especializados + regras simples (fallback)
        Retorna None se não conseguir interpretar, ou dict com funcao e params
        """
        import re
        msg = self._normalizar_mensagem(mensagem)
        print(f"🔍 [Regras] Analisando mensagem normalizada: '{msg}' (original: '{mensagem}')")
        
        # PRIMEIRO: Tenta usar os agentes especializados (arquitetura de múltiplos agentes)
        context = {
            "produtos": produtos,
            "carrinho": carrinho,
            "dados": dados
        }
        intention_result = self.intention_router.detect_intention(mensagem, msg, context)
        if intention_result:
            print(f"✅ [Agentes] Intenção detectada: {intention_result.get('intention')} -> {intention_result.get('funcao')}")
            return {
                "funcao": intention_result.get("funcao"),
                "params": intention_result.get("params", {})
            }
        
        # FALLBACK: Continua com as regras antigas para outras intenções não cobertas pelos agentes

        def _parse_quantidade_token(token: Optional[str]) -> int:
            if not token:
                return 1
            t = self._normalizar_mensagem(str(token))
            if not t:
                return 1
            if t.isdigit():
                return max(int(t), 1)
            mapa = {
                "um": 1,
                "uma": 1,
                "dois": 2,
                "duas": 2,
                "doise": 2,  # erro comum de digitação
                "tres": 3,
                "três": 3,
                "quatro": 4,
                "cinco": 5,
                "seis": 6,
                "sete": 7,
                "oito": 8,
                "nove": 9,
                "dez": 10,
            }
            if t in mapa:
                return mapa[t]
            # Heurística leve para "doi..." (ex: doise, doiss)
            if t.startswith("doi"):
                return 2
            return 1

        def _limpar_termos_finais_preenchimento(texto: str) -> str:
            # Remove termos como "então", "aí", "por favor" no final do pedido
            if not texto:
                return ""
            t = texto.strip()
            stop_finais = {
                "entao",
                "então",
                "ai",
                "aí",
                "pf",
                "pfv",
                "por favor",
                "porfavor",
                "porfav",
                "ok",
                "blz",
                "beleza",
                "valeu",
                "obg",
                "obrigado",
                "obrigada",
                "ta",
                "tá",
            }
            # normaliza espaços e remove repetidamente no final
            while True:
                t_norm = self._normalizar_mensagem(t)
                if not t_norm:
                    return ""
                tokens = t_norm.split()
                if not tokens:
                    return ""
                # tenta remover sufixos multi-palavra
                if t_norm.endswith("por favor"):
                    t = re.sub(r"\s*por\s+favor\s*$", "", t, flags=re.IGNORECASE).strip()
                    continue
                last = tokens[-1]
                if last in stop_finais:
                    t = re.sub(rf"\s*{re.escape(last)}\s*$", "", t, flags=re.IGNORECASE).strip()
                    continue
                return t.strip()

        def _obter_ultimo_produto_contexto() -> Optional[str]:
            # Prioridade: ultimo_produto_mencionado → pedido_contexto → ultimo_produto_adicionado → carrinho
            if dados:
                ultimo_mencionado = dados.get("ultimo_produto_mencionado")
                if ultimo_mencionado:
                    if isinstance(ultimo_mencionado, dict):
                        nome = (ultimo_mencionado.get("nome") or "").strip()
                        if nome:
                            return nome
                    else:
                        nome = str(ultimo_mencionado).strip()
                        if nome:
                            return nome

                pedido_contexto = dados.get("pedido_contexto") or []
                if pedido_contexto and isinstance(pedido_contexto, list):
                    ultimo = pedido_contexto[-1] or {}
                    if isinstance(ultimo, dict):
                        nome = (ultimo.get("nome") or "").strip()
                        if nome:
                            return nome

                ultimo_produto_adicionado = dados.get("ultimo_produto_adicionado")
                if ultimo_produto_adicionado:
                    if isinstance(ultimo_produto_adicionado, dict):
                        nome = (ultimo_produto_adicionado.get("nome") or "").strip()
                        if nome:
                            return nome
                    else:
                        nome = str(ultimo_produto_adicionado).strip()
                        if nome:
                            return nome

            if carrinho and isinstance(carrinho, list):
                try:
                    nome = (carrinho[-1].get("nome") or "").strip()
                    if nome:
                        return nome
                except Exception:
                    pass
            return None

        # CHAMAR ATENDENTE - DEVE vir PRIMEIRO, antes de qualquer detecção de pedido!
        if re.search(r'(chamar\s+atendente|quero\s+falar\s+com\s+(algu[eé]m|atendente|humano)|preciso\s+de\s+(um\s+)?(humano|atendente)|atendente\s+humano|quero\s+atendimento\s+humano|falar\s+com\s+atendente|ligar\s+atendente|chama\s+(algu[eé]m|atendente)\s+para\s+mi)', msg, re.IGNORECASE):
            print(f"📞 [Regras] Detecção de chamar atendente na mensagem: '{msg}'")
            return {"funcao": "chamar_atendente", "params": {}}

        # Saudações
        if re.match(r'^(oi|ola|olá|eae|e ai|eaí|bom dia|boa tarde|boa noite|hey|hi)[\s!?]*$', msg):
            return {"funcao": "conversar", "params": {"tipo_conversa": "saudacao"}}

        # Ver cardápio - perguntas sobre o que tem, quais produtos, etc.
        if re.search(r'(cardapio|cardápio|menu|lista|catalogo|catálogo)', msg):
            return {"funcao": "ver_cardapio", "params": {}}

        # PERGUNTAS SOBRE TAXA DE ENTREGA/FRETE - DEVE vir ANTES de perguntas de preço!
        # Detecta: "qual a taxa de entrega", "quanto é o frete", "quanto fica pra entregar", "vocês entregam", etc.
        # IMPORTANTE: Esta verificação deve vir ANTES de perguntas de preço de produtos!
        
        # Padrão 1: Perguntas diretas sobre taxa/frete/entrega
        if re.search(r'(taxa\s*(de\s*)?(entrega|delivery)|frete|valor\s*(da\s*)?(entrega|delivery)|pre[cç]o\s*(do\s*)?(frete|entrega|delivery))', msg, re.IGNORECASE):
            print(f"🚚 [Regras] Detecção de taxa de entrega (padrão 1) na mensagem: '{msg}'")
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}
        
        # Padrão 2: "quanto fica pra entregar", "quanto que fica pra entregar", etc.
        if re.search(r'quanto\s+(que\s+)?(fica|custa|é|e)\s+(pra|para|o\s*)?(entregar|entrega|delivery|frete)', msg, re.IGNORECASE):
            print(f"🚚 [Regras] Detecção de taxa de entrega (padrão 2) na mensagem: '{msg}'")
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}
        
        # Padrão 3: "quanto" + palavras de entrega/frete (em qualquer ordem)
        if re.search(r'quanto.*(entregar|entrega|delivery|frete)|(entregar|entrega|delivery|frete).*quanto', msg, re.IGNORECASE):
            print(f"🚚 [Regras] Detecção de taxa de entrega (padrão 3) na mensagem: '{msg}'")
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}
        
        # Padrão 4: "vocês entregam", "entregam em", "entregam na", "fazem entrega", etc.
        if re.search(r'(voc[eê]s?\s+entregam|entregam\s+(em|na|no|para|pra)|fazem\s+entrega|faz\s+entrega|tem\s+entrega|fazem\s+delivery|faz\s+delivery)', msg, re.IGNORECASE):
            print(f"🚚 [Regras] Detecção de taxa de entrega (padrão 4 - entrega) na mensagem: '{msg}'")
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}

        # Informação sobre produto ESPECÍFICO (DEVE vir ANTES da detecção genérica de "o que tem")
        # Detecta: "o que tem no X", "o que vem no X", "o que tem na X", "ingredientes do X", etc.
        if re.search(r'(o\s*q(ue)?\s*(vem|tem|ve|e)\s*(n[oa]|d[oa])|qu?al.*(ingrediente|composi[çc][aã]o)|ingredientes?\s*(d[oa])|composi[çc][aã]o)', msg):
            # Tenta extrair o produto mencionado após "no/na/do/da"
            match = re.search(r'(n[oa]|d[oa]|da|do)\s+([a-záàâãéêíóôõúç\-\s]+?)(\?|$|,|\.)', msg, re.IGNORECASE)
            if match:
                produto_extraido = match.group(2).strip()
                # Verifica se extraiu algo que parece um produto (não apenas palavras genéricas)
                palavras_genericas = ['cardapio', 'menu', 'lista', 'catalogo', 'catálogo', 'ai', 'aí', 'vocês', 'vcs']
                if produto_extraido and produto_extraido.lower() not in palavras_genericas and len(produto_extraido) > 2:
                    return {"funcao": "informar_sobre_produto", "params": {"produto_busca": produto_extraido}}
            
            # Tenta extrair produto de outra forma (produtos conhecidos)
            match2 = re.search(r'(pizza|x-?\w+|coca|guarana|água|agua|cerveja|batata|onion|hamburguer|hambúrguer|refrigerante|suco|bebida)[\w\s\-]*', msg, re.IGNORECASE)
            if match2:
                produto_match = match2.group(0).strip()
                return {"funcao": "informar_sobre_produto", "params": {"produto_busca": produto_match}}

        # PERGUNTAS DE PREÇO - DEVE vir ANTES da detecção genérica (muito importante!)
        # Detecta: "quanto fica", "quanto custa", "qual o preço", "qual preço", "quanto é"
        # MAS NÃO se for sobre entrega/frete (já foi detectado acima)
        if re.search(r'(quanto\s+(que\s+)?(fica|custa|é|e)|qual\s+(o\s+)?(pre[cç]o|valor)|pre[cç]o\s+(d[aeo]|de|do)|valor\s+(d[aeo]|de|do))', msg, re.IGNORECASE):
            # VERIFICA PRIMEIRO se é sobre entrega/frete (não produto)
            # Verifica múltiplos padrões para garantir que não perde nenhum caso
            if re.search(r'(entregar|entrega|delivery|frete|entregam|fazem\s+entrega|faz\s+entrega)', msg, re.IGNORECASE):
                print(f"🚚 [Regras] Detectado como taxa de entrega (dentro de verificação de preço) na mensagem: '{msg}'")
                return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}
            
            print(f"💰 [Regras] Detecção de preço na mensagem: '{msg}'")
            itens_preco = self._extrair_itens_pergunta_preco(mensagem)
            if itens_preco:
                resumo_itens = ", ".join(
                    [f"{i.get('quantidade', 1)}x {i.get('produto_busca', '')}" for i in itens_preco]
                )
                print(f"💰 [Regras] Itens extraídos: {resumo_itens}")
            if len(itens_preco) > 1:
                return {"funcao": "informar_sobre_produtos", "params": {"itens": itens_preco, "pergunta": msg}}
            if len(itens_preco) == 1:
                item = itens_preco[0]
                return {"funcao": "informar_sobre_produto", "params": {"produto_busca": item.get("produto_busca", ""), "pergunta": msg}}

            # Tenta extrair o produto mencionado após as palavras-chave de preço
            # Padrões: "quanto fica a X", "quanto custa a X", "qual o preço do X", "preço da X"
            match_preco = re.search(r'(?:quanto\s+(?:que\s+)?(?:fica|custa|é|e)|qual\s+(?:o\s+)?(?:pre[cç]o|valor)|pre[cç]o|valor)\s+(?:a|o|d[aeo]|de|do)?\s*([a-záàâãéêíóôõúç\-\s\d]+?)(\?|$|,|\.)', msg, re.IGNORECASE)
            if match_preco:
                produto_extraido = match_preco.group(1).strip()
                # Remove palavras genéricas que podem ter sido capturadas
                produto_extraido = re.sub(r'^(a|o|da|do|de)\s+', '', produto_extraido, flags=re.IGNORECASE).strip()
                # Remove quantidade no início (ex: "6 coca")
                produto_extraido = re.sub(r'^\d+\s*x?\s*', '', produto_extraido, flags=re.IGNORECASE).strip()
                palavras_genericas = ['cardapio', 'menu', 'lista', 'catalogo', 'catálogo', 'ai', 'aí', 'vocês', 'vcs', 'produto']
                if produto_extraido and produto_extraido.lower() not in palavras_genericas and len(produto_extraido) > 2:
                    return {"funcao": "informar_sobre_produto", "params": {"produto_busca": produto_extraido, "pergunta": msg}}
            
            # Se não extraiu por regex, tenta buscar produtos conhecidos na mensagem
            match_produto_preco = re.search(r'(pizza|x-?\w+|coca|guarana|água|agua|cerveja|batata|onion|hamburguer|hambúrguer|refrigerante|suco|bebida|[\d]+ml|[\d]+\s*ml)[\w\s\-]*', msg, re.IGNORECASE)
            if match_produto_preco:
                produto_preco = match_produto_preco.group(0).strip()
                produto_preco = re.sub(r'^\d+\s*x?\s*', '', produto_preco, flags=re.IGNORECASE).strip()
                return {"funcao": "informar_sobre_produto", "params": {"produto_busca": produto_preco, "pergunta": msg}}

        # Perguntas sobre o que tem disponível (genérico - DEVE vir DEPOIS da detecção de produto específico)
        if re.search(r'(o\s*que\s*(mais\s*)?(tem|vende|voces? tem|vcs tem)|quais?\s*(que\s*)?(tem|produto|op[cç]oes)|mostra\s*(ai|aí|os\s*produto)|que\s*produto|tem\s*o\s*que)', msg):
            return {"funcao": "ver_cardapio", "params": {}}

        # Ver combos
        if re.search(r'(combo|combos|promocao|promocoes)', msg):
            return {"funcao": "ver_combos", "params": {}}

        # Ver carrinho
        if re.search(r'(quanto\s*(ta|tá|esta)|meu\s*pedido|carrinho|o\s*que\s*(eu\s*)?pedi)', msg):
            return {"funcao": "ver_carrinho", "params": {}}

        # Finalizar pedido (explícito)
        if re.search(r'(finalizar|fechar|so\s+isso|so\s+apenas|somente\s+isso|so\s+isso\s+mesmo|pronto|e\s+isso|acabou|era\s+isso|so$)', msg):
            return {"funcao": "finalizar_pedido", "params": {}}

        # "nao", "não", "nao quero", "não quero" = CONTEXTUAL
        # - Se tem carrinho com itens → finalizar pedido (resposta a "mais alguma coisa?")
        # - Se carrinho vazio → perguntar o que deseja
        if re.match(r'^(n[aã]o|nao|não)(\s+quero)?[\s!.]*$', msg):
            if carrinho and len(carrinho) > 0:
                # Tem itens no carrinho, "não" = não quero mais nada = finalizar
                return {"funcao": "finalizar_pedido", "params": {}}
            else:
                # Carrinho vazio, "não" pode ser resposta a uma pergunta
                return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}

        # Remover produto
        if re.search(r'(tira|remove|cancela|retira)\s+(?:a|o)?\s*(.+)', msg):
            match = re.search(r'(tira|remove|cancela|retira)\s+(?:a|o)?\s*(.+)', msg)
            if match:
                return {"funcao": "remover_produto", "params": {"produto_busca": match.group(2).strip()}}

        # NOTA: Detecção de "iniciar novo pedido" agora é feita pelo IniciarPedidoAgent
        # (já processado acima pelos agentes especializados antes das regras antigas)

        # Ver adicionais
        if re.search(r'(adicionais|extras|o\s*que\s*posso\s*adicionar)', msg):
            return {"funcao": "ver_adicionais", "params": {}}

        # Pedido com múltiplos itens (ex: "1 x bacon e 1 coca")
        itens_pedido = self._extrair_itens_pedido(mensagem)
        if len(itens_pedido) > 1:
            return {"funcao": "adicionar_produtos", "params": {"itens": itens_pedido}}

        # Pedido só com QUANTIDADE (sem produto): usa o último produto do contexto
        # Ex: "me vê dois", "quero 2", "manda duas então"
        match_qtd_only = re.match(
            r'^(?:(?:me\s+)?(?:ve|v[eê]|manda|traz)|(?:quero|qro)|(?:pode\s+ser|vou\s+querer))\s+'
            r'(um|uma|duas?|dois|doise|tres|tr[eê]s|\d+)'
            r'(?:\s*x)?'
            r'(?:\s+(?:entao|ai|pf|pfv|por\s+favor))?\s*$',
            msg,
            re.IGNORECASE,
        )
        if match_qtd_only:
            quantidade = _parse_quantidade_token(match_qtd_only.group(1))
            ultimo = _obter_ultimo_produto_contexto()
            if ultimo:
                return {
                    "funcao": "adicionar_produto",
                    "params": {"produto_busca": ultimo, "quantidade": max(int(quantidade), 1)},
                }
            return {"funcao": "conversar", "params": {"tipo_conversa": "pergunta_vaga"}}

        # Adicionar produto (padrões: "quero X", "me ve X", "manda X", "X por favor")
        # IMPORTANTE: Verificar ANTES da personalização para capturar "quero X sem Y"
        patterns_pedido = [
            # (regex, group_qtd, group_produto)
            (r'(?:quero|qro)\s+(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+)\s*)?(.+)', 1, 2),
            (r'(?:me\s+)?(?:ve|vê|manda|traz)\s+(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+)\s*)?(.+)', 1, 2),
            (r'(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+))\s+(.+?)(?:\s+por\s+favor)?$', 1, 2),
            (r'(?:pode\s+ser|vou\s+querer)\s+(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+)\s*)?(.+)', 1, 2),
        ]

        for pattern, qtd_group, produto_group in patterns_pedido:
            match = re.search(pattern, msg)
            if match:
                qtd_token = (match.group(qtd_group) or "").strip() if match.lastindex and match.lastindex >= qtd_group else ""
                produto_completo = (match.group(produto_group) or "").strip() if match.lastindex and match.lastindex >= produto_group else ""

                # Quantidade pode vir como "2", "dois", "duas" etc.
                quantidade = _parse_quantidade_token(qtd_token)

                # Fallback: casos tipo "2x bacon" dentro do produto (mesmo sem qtd_token)
                qtd_match = re.search(r'^(\d+)\s*x?\s*', produto_completo)
                if qtd_match:
                    quantidade = max(int(qtd_match.group(1)), 1)
                    produto_completo = produto_completo[qtd_match.end():].strip()
                
                # Verifica se tem personalização junto (sem X, com X, mais X)
                personalizacao = None
                # Remove personalização do nome do produto
                produto_limpo = produto_completo
                
                # Detecta "sem X" e remove do nome do produto
                match_sem = re.search(r'\s+sem\s+(\w+)', produto_completo, re.IGNORECASE)
                if match_sem:
                    personalizacao = {"acao": "remover_ingrediente", "item": match_sem.group(1)}
                    produto_limpo = re.sub(r'\s+sem\s+\w+', '', produto_completo, flags=re.IGNORECASE).strip()
                
                # Detecta "com X extra" ou "mais X" e remove do nome do produto
                match_extra = re.search(r'\s+(?:com|mais|extra)\s+(\w+)', produto_completo, re.IGNORECASE)
                if match_extra and not personalizacao:
                    personalizacao = {"acao": "adicionar_extra", "item": match_extra.group(1)}
                    produto_limpo = re.sub(r'\s+(?:com|mais|extra)\s+\w+', '', produto_completo, flags=re.IGNORECASE).strip()
                
                produto_limpo = _limpar_termos_finais_preenchimento(produto_limpo)
                # Se ficou algo do tipo "então/ai/pf", usa contexto do último produto mencionado
                if not produto_limpo or len(self._normalizar_mensagem(produto_limpo)) < 2:
                    ultimo = _obter_ultimo_produto_contexto()
                    if ultimo:
                        produto_limpo = ultimo

                # Retorna adicionar produto com personalização se houver
                params = {"produto_busca": produto_limpo, "quantidade": max(int(quantidade), 1)}
                if personalizacao:
                    params["personalizacao"] = personalizacao
                    print(f"   🎯 Detectado produto + personalização: {produto_limpo} {personalizacao}")
                
                return {"funcao": "adicionar_produto", "params": params}

        # Personalização (sem/tira ingrediente) - APENAS se não tiver produto na mensagem E carrinho tem itens
        # Verifica se tem carrinho com itens antes de personalizar
        if carrinho and len(carrinho) > 0:
            # Verifica se NÃO tem padrão de adicionar produto na mensagem
            tem_produto_na_mensagem = any(re.search(pattern, msg) for pattern in [
                r'(?:quero|qro)\s+',
                r'(?:me\s+)?(?:ve|vê|manda|traz)\s+',
                r'(?:uma?|duas?|dois|\d+)\s+',
            ])
            
            # Só personaliza se NÃO tiver produto na mensagem
            if not tem_produto_na_mensagem:
                if re.search(r'sem\s+(\w+)', msg):
                    match = re.search(r'sem\s+(\w+)', msg)
                    if match:
                        return {"funcao": "personalizar_produto", "params": {"acao": "remover_ingrediente", "item": match.group(1)}}

                # Adicional extra
                if re.search(r'(mais|extra|adiciona)\s+(\w+)', msg):
                    match = re.search(r'(mais|extra|adiciona)\s+(\w+)', msg)
                    if match:
                        return {"funcao": "personalizar_produto", "params": {"acao": "adicionar_extra", "item": match.group(2)}}

            # Adicional extra
            if re.search(r'(mais|extra|adiciona)\s+(\w+)', msg):
                match = re.search(r'(mais|extra|adiciona)\s+(\w+)', msg)
                if match:
                    return {"funcao": "personalizar_produto", "params": {"acao": "adicionar_extra", "item": match.group(2)}}

        # ÚLTIMO RECURSO: Verifica se a mensagem é um nome de produto direto
        # Isso captura casos como "coca", "pizza calabresa"
        if len(msg) >= 2 and len(msg) <= 50:
            # Verifica se não é uma pergunta ou frase comum
            palavras_ignorar = [
                'sim', 'ok', 'obrigado', 'obrigada', 'valeu', 'blz', 'beleza', 'certo', 'ta', 'tá',
                'nao', 'não', 'qual', 'quais', 'que', 'como', 'onde', 'quando', 'porque', 'por que',
                'so', 'so isso', 'só', 'só isso', 'isso', 'somente', 'apenas', 'nada', 'nada mais',
                # evita interpretar quantidade/enchimento como produto
                'um', 'uma', 'dois', 'duas', 'doise', 'tres', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove', 'dez',
                'entao', 'então', 'ai', 'aí', 'pf', 'pfv', 'por favor'
            ]
            # Verifica se não é uma pergunta (termina com ?)
            if msg.endswith('?'):
                return None
            # Verifica se não contém palavras interrogativas
            if msg in palavras_ignorar or any(p in msg for p in palavras_ignorar):
                return None
            # Tenta como pedido de produto
            return {"funcao": "adicionar_produto", "params": {"produto_busca": msg, "quantidade": 1}}

        # Se não encontrou padrão específico, retorna None para tentar Groq ou fallback
        return None

    async def _interpretar_intencao_ia(self, mensagem: str, produtos: List[Dict], carrinho: List[Dict]) -> Dict[str, Any]:
        """
        Usa a IA (Groq) para interpretar a intenção do cliente.
        Retorna um dict com a função a ser chamada e os parâmetros.

        Exemplo de retorno:
        {"funcao": "adicionar_produto", "params": {"produto_busca": "coca", "quantidade": 1}}
        {"funcao": "finalizar_pedido", "params": {}}
        {"funcao": "responder_conversa", "params": {"resposta": "Olá! Como posso ajudar?"}}
        """
        # FASE 1: IA como roteador principal.
        # Antes da IA, aplicamos apenas GUARDRAILS mínimos (proteções críticas).
        guardrail = self._interpretar_intencao_guardrails(mensagem)
        if guardrail:
            print(f"🛡️ Guardrail interpretou: {guardrail['funcao']}({guardrail.get('params', {})})")
            return guardrail

        # SE GROQ_API_KEY não estiver configurado ou estiver vazio, usa fallback
        if not GROQ_API_KEY or not GROQ_API_KEY.strip():
            print(f"⚠️ GROQ_API_KEY não configurado ou vazio, usando fallback")
            # Tenta usar regras novamente como fallback mais inteligente
            resultado_fallback = self._interpretar_intencao_regras(mensagem, produtos, carrinho)
            if resultado_fallback:
                return resultado_fallback
            return {"funcao": "conversar", "params": {"tipo_conversa": "pergunta_vaga"}}

        # Monta lista de produtos para o prompt
        produtos_lista = "\n".join([f"- {p['nome']} (R$ {p['preco']:.2f})" for p in produtos[:30]])

        # Monta carrinho atual
        if carrinho:
            carrinho_atual = "\n".join([f"- {item['nome']} x{item.get('quantidade', 1)}" for item in carrinho])
        else:
            carrinho_atual = "Carrinho vazio"

        # Prepara o prompt
        prompt_sistema = AI_INTERPRETER_PROMPT.format(
            produtos_lista=produtos_lista,
            carrinho_atual=carrinho_atual
        )
        # Guardrails anti-alucinação para reduzir escolhas erradas de função
        prompt_sistema = build_system_prompt(prompt_sistema, require_json_object=False)

        # FASE 2 (RAG): injeta contexto do catálogo baseado na mensagem para melhorar entendimento
        contexto_catalogo = self._buscar_contexto_catalogo_rag(mensagem, limit=8)
        contexto_rag_usado = bool(contexto_catalogo)
        if contexto_catalogo:
            prompt_sistema += (
                "\n\n=== CONTEXTO DO CATÁLOGO (RAG) ===\n"
                f"{contexto_catalogo}\n\n"
                "Use este contexto para entender ingredientes/descrições e para escolher o produto correto.\n"
                "Se precisar, use o NOME mais próximo do catálogo para preencher produto_busca.\n"
            )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": mensagem}
                    ],
                    "tools": AI_FUNCTIONS,
                    "tool_choice": "auto",  # IA decide se precisa chamar função
                    "temperature": 0.1,  # Baixa temperatura para mais precisão
                    "max_tokens": 200,
                }

                # Verifica se a chave API está configurada
                if not GROQ_API_KEY or not GROQ_API_KEY.strip():
                    print("⚠️ GROQ_API_KEY não configurada - usando fallback inteligente")
                    raise ValueError("GROQ_API_KEY não configurada")
                
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
                    "Content-Type": "application/json"
                }

                print(f"🧠 IA interpretando: '{mensagem}'")
                inicio = time.time()
                response = await client.post(GROQ_API_URL, json=payload, headers=headers)
                tempo_resposta_ms = (time.time() - inicio) * 1000

                if response.status_code == 200:
                    result = response.json()
                    message = result.get("choices", [{}])[0].get("message", {})

                    # Verifica se tem tool_calls
                    tool_calls = message.get("tool_calls", [])
                    if tool_calls:
                        tool_call = tool_calls[0]
                        funcao = tool_call.get("function", {}).get("name", "responder_conversa")
                        args_str = tool_call.get("function", {}).get("arguments", "{}")

                        try:
                            params = json.loads(args_str)
                        except:
                            params = {}

                        print(f"🎯 IA decidiu: {funcao}({params})")
                        
                        # FASE 4: Log de decisão da IA
                        if self.observability:
                            self.observability.log_decisao_ia(
                                mensagem=mensagem,
                                funcao_escolhida=funcao,
                                params=params,
                                tempo_resposta_ms=tempo_resposta_ms,
                                contexto_rag_usado=contexto_rag_usado,
                            )
                        
                        return {"funcao": funcao, "params": params}

                    # Se não tem tool_calls, trata como conversa
                    content = message.get("content", "")
                    print(f"⚠️ IA não chamou função, tratando como conversa")
                    return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica", "contexto": content}}

                else:
                    print(f"❌ Erro na API Groq: {response.status_code}")
                    # Ainda assim tenta conversar
                    return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}

        except httpx.TimeoutException as e:
            # FASE 4: Log de timeout
            if self.observability:
                self.observability.log_timeout(mensagem, timeout_segundos=15.0)
            print(f"⏰ Timeout ao interpretar intenção: {e}")
            # Tenta usar regras como fallback quando a IA falha
            resultado_fallback = self._interpretar_intencao_regras(mensagem, produtos, carrinho)
            if resultado_fallback:
                if self.observability:
                    self.observability.log_fallback(mensagem, "timeout", resultado_fallback.get("funcao", "conversar"))
                print(f"🔄 Usando regras como fallback após timeout da IA")
                return resultado_fallback
            return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}
        except Exception as e:
            # FASE 4: Log de erro
            if self.observability:
                self.observability.log_erro(mensagem, e, {"empresa_id": self.empresa_id})
            print(f"❌ Erro ao interpretar intenção: {e}")
            # Tenta usar regras como fallback quando a IA falha
            resultado_fallback = self._interpretar_intencao_regras(mensagem, produtos, carrinho)
            if resultado_fallback:
                if self.observability:
                    self.observability.log_fallback(mensagem, f"erro: {type(e).__name__}", resultado_fallback.get("funcao", "conversar"))
                print(f"🔄 Usando regras como fallback após erro da IA")
                return resultado_fallback
            return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}

    def _buscar_contexto_catalogo_rag(self, texto: str, limit: int = 8) -> str:
        """
        RAG simples (fase 2): busca itens relevantes no catálogo (produtos/receitas/combos)
        e retorna um texto curto para injetar em prompts.
        """
        try:
            termo = (texto or "").strip()
            if not termo:
                return ""

            # Busca global já consulta nome/descrição de produtos/receitas/combos
            res = BuscaGlobalService(self.db).buscar(
                empresa_id=int(self.empresa_id),
                termo=termo,
                apenas_disponiveis=True,
                apenas_ativos=True,
                limit=10,
                page=1,
            )

            itens: List[Any] = []
            try:
                itens.extend(res.produtos or [])
                itens.extend(res.receitas or [])
                itens.extend(res.combos or [])
            except Exception:
                # fallback defensivo
                pass

            if not itens:
                return ""

            def _truncate(s: Optional[str], n: int = 220) -> str:
                if not s:
                    return ""
                s = " ".join(str(s).split())
                return s if len(s) <= n else (s[: n - 1] + "…")

            linhas: List[str] = []
            for item in itens[: max(int(limit), 1)]:
                nome = getattr(item, "nome", None) or (item.get("nome") if isinstance(item, dict) else "")
                tipo = getattr(item, "tipo", None) or (item.get("tipo") if isinstance(item, dict) else "")
                preco = getattr(item, "preco", None) if not isinstance(item, dict) else item.get("preco")
                descricao = getattr(item, "descricao", None) if not isinstance(item, dict) else item.get("descricao")

                nome = str(nome or "").strip()
                if not nome:
                    continue

                preco_str = ""
                try:
                    if preco is not None:
                        preco_str = f" — R$ {float(preco):.2f}"
                except Exception:
                    preco_str = ""

                desc_str = _truncate(descricao)
                if desc_str:
                    linhas.append(f"- [{tipo}] {nome}{preco_str}\n  {desc_str}")
                else:
                    linhas.append(f"- [{tipo}] {nome}{preco_str}")

            return "\n".join(linhas).strip()
        except Exception as e:
            print(f"⚠️ Erro no RAG do catálogo: {e}")
            return ""

    def _resumir_historico_para_ia(self, historico: List[Dict], max_mensagens: int = 8) -> List[Dict]:
        """
        FASE 3: Resumir histórico quando muito longo, mantendo contexto relevante.
        Prioriza mensagens recentes e remove redundâncias.
        """
        if not historico or len(historico) <= max_mensagens:
            return historico[-max_mensagens:] if historico else []
        
        # Pega últimas N mensagens (mais recentes são mais relevantes)
        recentes = historico[-max_mensagens:]
        
        # Se histórico é muito longo, tenta resumir mantendo início (contexto) e fim (recente)
        if len(historico) > max_mensagens * 2:
            # Mantém primeira mensagem (contexto inicial) + últimas N
            if len(historico) > 1:
                return [historico[0]] + recentes[1:]
        
        return recentes

    def _resolver_referencias_na_mensagem(
        self, 
        mensagem: str, 
        pedido_contexto: List[Dict], 
        carrinho: List[Dict],
        dados: Dict
    ) -> str:
        """
        FASE 3: Resolve referências como "esse", "o último", "o de frango" na mensagem.
        Retorna mensagem com referências substituídas por nomes concretos.
        """
        import re
        
        msg = mensagem
        if not msg or not msg.strip():
            return msg
        
        msg_lower = msg.lower()
        
        # Resolve "esse", "esse aí", "esse último"
        if re.search(r'\b(esse|essa|isso|esse\s+a[ií]|esse\s+último|último)\b', msg_lower):
            # Busca último item mencionado/adicionado
            ultimo_item = None
            
            # Prioridade: último do pedido_contexto > último do carrinho > último mencionado
            if pedido_contexto:
                ultimo_item = pedido_contexto[-1].get('nome', '')
            elif carrinho:
                ultimo_item = carrinho[-1].get('nome', '')
            else:
                ultimo_mencionado = dados.get('ultimo_produto_mencionado')
                if isinstance(ultimo_mencionado, dict):
                    ultimo_item = ultimo_mencionado.get('nome', '')
                elif isinstance(ultimo_mencionado, str):
                    ultimo_item = ultimo_mencionado
            
            if ultimo_item:
                # Substitui referências pelo nome do produto
                msg = re.sub(
                    r'\b(esse|essa|isso|esse\s+a[ií]|esse\s+último|último)\b',
                    ultimo_item,
                    msg,
                    flags=re.IGNORECASE,
                    count=1  # Substitui apenas a primeira ocorrência
                )
                print(f"🔗 Referência resolvida: '{mensagem}' → '{msg}' (produto: {ultimo_item})")
        
        # Resolve "o de [ingrediente]" ou "a de [ingrediente]" (ex: "o de frango", "a de calabresa")
        match_ingrediente = re.search(r'\b(o|a)\s+de\s+(\w+)', msg_lower)
        if match_ingrediente:
            ingrediente = match_ingrediente.group(2)
            
            # Busca produtos que contenham esse ingrediente no nome ou descrição
            todos_produtos = self._buscar_todos_produtos()
            for produto in todos_produtos:
                nome_prod = str(produto.get('nome', '')).lower()
                desc_prod = str(produto.get('descricao', '')).lower()
                
                if ingrediente in nome_prod or ingrediente in desc_prod:
                    # Substitui "o de X" pelo nome do produto
                    msg = re.sub(
                        rf'\b(o|a)\s+de\s+{re.escape(ingrediente)}\b',
                        produto.get('nome', ''),
                        msg,
                        flags=re.IGNORECASE,
                        count=1
                    )
                    print(f"🔗 Referência por ingrediente resolvida: '{mensagem}' → '{msg}' (produto: {produto.get('nome')})")
                    break
        
        return msg

    def _resumir_contexto_pedido(
        self, 
        pedido_contexto: List[Dict], 
        carrinho: List[Dict]
    ) -> str:
        """
        FASE 3: Resume contexto do pedido de forma mais inteligente e compacta.
        """
        itens = pedido_contexto if pedido_contexto else (carrinho if carrinho else [])
        
        if not itens:
            return "\n📝 PEDIDO: Nenhum item anotado ainda.\n"
        
        # Resumo compacto
        linhas = ["\n📝 PEDIDO ATUAL:"]
        total = 0
        
        for item in itens:
            qtd = item.get('quantidade', 1)
            nome = item.get('nome', '')
            preco_unit = item.get('preco', 0)
            preco_item = preco_unit * qtd
            total += preco_item
            
            # Formato compacto: "2x Nome - R$ X.XX"
            linha = f"  • {qtd}x {nome} - R$ {preco_item:.2f}"
            
            # Adiciona personalizações de forma compacta
            removidos = item.get('removidos', [])
            adicionais = item.get('adicionais', [])
            if removidos:
                linha += f" (sem: {', '.join(removidos[:2])})"  # Limita a 2 para não ficar muito longo
            if adicionais:
                adic_str = ', '.join([str(a.get('nome', a) if isinstance(a, dict) else a) for a in adicionais[:2]])
                linha += f" (+{adic_str})"
            
            linhas.append(linha)
        
        linhas.append(f"💰 Total: R$ {total:.2f}\n")
        
        return "\n".join(linhas)

    def _interpretar_intencao_guardrails(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """
        Guardrails mínimos (proteções críticas) executados ANTES da IA.
        Importante: aqui NÃO pode entrar lógica ampla de roteamento (para não virar "regex first").
        """
        import re

        msg = self._normalizar_mensagem(mensagem or "")
        if not msg:
            return None

        # 1) Chamar atendente humano (sempre prioriza)
        if re.search(
            r'(chamar\s+atendente|quero\s+falar\s+com\s+(algu[eé]m|atendente|humano)|preciso\s+de\s+(um\s+)?(humano|atendente)|atendente\s+humano|quero\s+atendimento\s+humano|falar\s+com\s+atendente|ligar\s+atendente|chama\s+(algu[eé]m|atendente)\s+para\s+mi)',
            msg,
            re.IGNORECASE,
        ):
            return {"funcao": "chamar_atendente", "params": {}}

        # 2) Taxa de entrega / frete (prioriza para evitar confusão com "quanto custa")
        if re.search(
            r'(taxa\s*(de\s*)?(entrega|delivery)|frete|valor\s*(da\s*)?(entrega|delivery)|pre[cç]o\s*(do\s*)?(frete|entrega|delivery))',
            msg,
            re.IGNORECASE,
        ):
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}

        if re.search(
            r'quanto\s+(que\s+)?(fica|custa|é|e)\s+(pra|para|o\s*)?(entregar|entrega|delivery|frete)',
            msg,
            re.IGNORECASE,
        ):
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}

        if re.search(
            r'(voc[eê]s?\s+entregam|entregam\s+(em|na|no|para|pra)|fazem\s+entrega|faz\s+entrega|tem\s+entrega|fazem\s+delivery|faz\s+delivery)',
            msg,
            re.IGNORECASE,
        ):
            return {"funcao": "calcular_taxa_entrega", "params": {"mensagem_original": mensagem}}

        return None

    def _buscar_produto_por_termo(self, termo: str, produtos: List[Dict] = None) -> Optional[Dict]:
        """
        Busca um produto usando busca inteligente no banco (produtos + receitas + combos).
        Se produtos for fornecido, também busca na lista como fallback.
        Usa busca fuzzy com correção de erros e suporte a variações.
        """
        return self.produto_service.buscar_produto_por_termo(termo, produtos)

    def _gerar_mensagem_boas_vindas(self) -> str:
        """
        Gera mensagem de boas-vindas CURTA e NATURAL
        """
        return self.formatters.gerar_mensagem_boas_vindas(self._buscar_promocoes)

    def _load_chatbot_config(self):
        """Carrega configurações do chatbot para a empresa"""
        self.config_loader._load_chatbot_config()
        self._config_cache = self.config_loader.get_chatbot_config()

    def _get_chatbot_config(self):
        """Retorna configuração do chatbot (com cache)"""
        return self.config_loader.get_chatbot_config()

    def _obter_link_cardapio(self) -> str:
        """Obtém o link do cardápio da empresa"""
        return self.config_loader.obter_link_cardapio()

    def _obter_mensagem_final_pedido(self) -> str:
        """
        Retorna a mensagem final apropriada baseada em aceita_pedidos_whatsapp.
        Se aceita pedidos: "Quer adicionar ao pedido? 😊"
        Se não aceita: mensagem com link do cardápio
        """
        return self.config_loader.obter_mensagem_final_pedido()

    def _gerar_mensagem_boas_vindas_conversacional(self) -> str:
        """Gera mensagem de boas-vindas para modo conversacional com botões"""
        return self.formatters.gerar_mensagem_boas_vindas_conversacional(
            self._get_chatbot_config, self._obter_link_cardapio
        )

    async def _processar_conversa_ia(self, user_id: str, mensagem: str, dados: dict) -> str:
        """
        Processa mensagem no modo conversacional usando IA livre.
        A IA conversa naturalmente, tira dúvidas e anota o pedido.
        """
        import json
        import re

        # Obtém o estado atual da conversa
        estado, dados_atualizados = self._obter_estado_conversa(user_id)
        # Atualiza dados com os mais recentes
        dados.update(dados_atualizados)
        self._sincronizar_carrinho_dados(user_id, dados)

        print(f"💬 [Conversacional] Mensagem recebida (user_id={user_id}): {mensagem}")
        
        # NOTA: Não bloqueamos aqui perguntas sobre preços/informações de produtos.
        # A IA interpreta a intenção e diferencia perguntas (informar_sobre_produto) de pedidos (adicionar_produto).
        # A verificação de aceita_pedidos_whatsapp é feita DEPOIS da interpretação da IA, nas linhas 5709-5733,
        # onde bloqueamos apenas ações reais de pedido (adicionar_produto, finalizar_pedido).
        
        # PRIMEIRO: Tenta interpretar com regras (funciona mesmo sem IA)
        # Isso garante que perguntas sobre produtos específicos sejam detectadas
        todos_produtos = self._buscar_todos_produtos()
        carrinho = dados.get('carrinho', [])
        pedido_contexto = dados.get('pedido_contexto', [])
        
        # VERIFICAÇÃO PRIORITÁRIA: Se detectar finalizar_pedido, segue fluxo estruturado
        resultado_finalizar = self._interpretar_intencao_regras(mensagem, todos_produtos, carrinho, dados)
        if resultado_finalizar and resultado_finalizar.get("funcao") == "finalizar_pedido":
            # Se tem itens no carrinho ou no pedido_contexto, inicia fluxo de finalização
            if carrinho or pedido_contexto:
                # Se tem pedido_contexto mas não carrinho, converte primeiro
                if pedido_contexto and not carrinho:
                    dados['carrinho'] = self._converter_contexto_para_carrinho(pedido_contexto)
                    dados['pedido_contexto'] = pedido_contexto
                
                print("🛒 [Modo Conversacional] Detectado finalizar_pedido, iniciando fluxo estruturado")
                return self._perguntar_entrega_ou_retirada(user_id, dados)
            else:
                return "Opa, seu carrinho tá vazio ainda! O que vai querer?"
        
        msg_lower = mensagem.lower()

        # PERGUNTAS DE PREÇO (inclui múltiplos itens) - prioridade alta
        if re.search(r'(quanto\s+(que\s+)?(fica|custa|é|e)|qual\s+(o\s+)?(pre[cç]o|valor)|pre[cç]o\s+(d[aeo]|de|do)|valor\s+(d[aeo]|de|do))', msg_lower, re.IGNORECASE):
            print(f"💰 [Conversacional] Detecção de preço na mensagem: '{mensagem}'")
            itens_preco = self._extrair_itens_pergunta_preco(mensagem)
            if itens_preco:
                resumo_itens = ", ".join(
                    [f"{i.get('quantidade', 1)}x {i.get('produto_busca', '')}" for i in itens_preco]
                )
                print(f"💰 [Conversacional] Itens extraídos: {resumo_itens}")
            else:
                print("💰 [Conversacional] Nenhum item extraído para preço")
            if len(itens_preco) > 1:
                resposta_preco = self._gerar_resposta_preco_itens(user_id, dados, itens_preco, todos_produtos)
                self._salvar_estado_conversa(user_id, estado, dados)
                return resposta_preco
            if len(itens_preco) == 1:
                item = itens_preco[0]
                produto = self._resolver_produto_para_preco(
                    item.get("produto_busca", ""),
                    item.get("produto_busca_alt", ""),
                    bool(item.get("prefer_alt", False)),
                    todos_produtos
                )
                if produto:
                    # Memoriza o último produto mencionado/consultado para pedidos do tipo "me vê dois"
                    try:
                        dados["ultimo_produto_mencionado"] = {
                            "nome": produto.get("nome"),
                            "tipo": produto.get("tipo", "produto"),
                            "id": produto.get("id"),
                        }
                    except Exception:
                        pass
                    return await self._gerar_resposta_sobre_produto(user_id, produto, mensagem, dados)
                return "Qual produto você quer saber o preço? Me fala o nome!"

        # ANTES DE TUDO: Detecta perguntas sobre ingredientes/composição de produtos
        # Isso funciona mesmo sem IA e deve ter prioridade
        
        # Detecta padrões como "O que vem nele", "Que tem nele" (sem mencionar produto)
        padroes_nele = [
            r'o\s+que\s+(?:vem|tem)\s+nele',
            r'que\s+(?:vem|tem)\s+nele',
            r'o\s+que\s+(?:vem|tem)\s+n[oa]\s+ele',
            r'que\s+(?:vem|tem)\s+n[oa]\s+ele'
        ]
        for padrao in padroes_nele:
            if re.search(padrao, msg_lower):
                produto_encontrado = None
                fonte_produto = None
                
                # 1. Tenta usar pedido_contexto (último produto mencionado na conversa)
                if pedido_contexto:
                    ultimo_produto = pedido_contexto[-1]
                    produto_encontrado = self._buscar_produto_por_termo(ultimo_produto.get('nome', ''), todos_produtos)
                    if produto_encontrado:
                        fonte_produto = "pedido_contexto"
                
                # 2. Se não encontrou, tenta usar o carrinho
                if not produto_encontrado and carrinho:
                    ultimo_item_carrinho = carrinho[-1]
                    produto_encontrado = self._buscar_produto_por_termo(ultimo_item_carrinho.get('nome', ''), todos_produtos)
                    if produto_encontrado:
                        fonte_produto = "carrinho"
                
                # 3. Se não encontrou, tenta usar ultimo_produto_adicionado
                if not produto_encontrado:
                    ultimo_produto_adicionado = dados.get('ultimo_produto_adicionado')
                    if ultimo_produto_adicionado:
                        if isinstance(ultimo_produto_adicionado, dict):
                            nome_produto = ultimo_produto_adicionado.get('nome', '')
                        else:
                            nome_produto = str(ultimo_produto_adicionado)
                        produto_encontrado = self._buscar_produto_por_termo(nome_produto, todos_produtos)
                        if produto_encontrado:
                            fonte_produto = "ultimo_produto_adicionado"
                
                # 4. Se ainda não encontrou, busca no histórico da conversa (mensagens do usuário e assistente)
                if not produto_encontrado:
                    historico = dados.get('historico', [])
                    # Busca nas últimas 10 mensagens (usuário e assistente)
                    for msg in reversed(historico[-10:]):
                        conteudo = msg.get('content', '')
                        role = msg.get('role', '')
                        
                        # 4.1. Extrai produtos mencionados com * (formato markdown)
                        matches_asterisco = re.findall(r'\*([^*]+)\*', conteudo)
                        for match in reversed(matches_asterisco):
                            # Ignora palavras comuns que não são produtos
                            palavras_ignorar = ['cardápio', 'cardapio', 'menu', 'pedido', 'carrinho', 'total', 'ingredientes', 'adicionais', 'sim', 'temos', 'quero', 'adicionar']
                            match_limpo = match.strip()
                            if match_limpo.lower() not in palavras_ignorar and len(match_limpo) > 3:
                                # Tenta buscar o produto
                                produto_encontrado = self._buscar_produto_por_termo(match_limpo, todos_produtos)
                                if produto_encontrado:
                                    fonte_produto = f"historico_{role}"
                                    print(f"🔍 Produto encontrado no histórico ({role}): '{match_limpo}' -> '{produto_encontrado['nome']}'")
                                    break
                        
                        if produto_encontrado:
                            break
                        
                        # 4.2. Se não encontrou com *, busca por padrões de nomes de produtos na mensagem do usuário
                        if role == 'user' and not produto_encontrado:
                            # Extrai possíveis nomes de produtos (palavras com mais de 3 caracteres que não são comuns)
                            palavras_comuns = ['tem', 'têm', 'vocês', 'vcs', 'quero', 'gostaria', 'pode', 'me', 've', 'ver', 'mostra', 'mostrar', 'o', 'que', 'vem', 'nele', 'nela', 'tem', 'tem', 'qual', 'quais', 'quero', 'adicionar', 'pedir']
                            palavras_msg = re.findall(r'\b[a-záàâãéêíóôõúç\-]+\b', conteudo.lower())
                            for palavra in reversed(palavras_msg):
                                if len(palavra) > 3 and palavra not in palavras_comuns:
                                    produto_encontrado = self._buscar_produto_por_termo(palavra, todos_produtos)
                                    if produto_encontrado:
                                        fonte_produto = f"historico_user_palavra"
                                        print(f"🔍 Produto encontrado no histórico (palavra do usuário): '{palavra}' -> '{produto_encontrado['nome']}'")
                                        break
                        
                        if produto_encontrado:
                            break
                        
                        # 4.3. Busca por padrões específicos como "x-burger", "x burger", "hamburguer", etc
                        if not produto_encontrado:
                            padroes_produtos = [
                                r'x[\s\-]?([a-z]+)',  # x-burger, x burger, xbacon
                                r'([a-z]+)[\s\-]?burger',  # hamburguer, hamburger
                                r'pizza[\s\-]?([a-z]+)',  # pizza calabresa
                            ]
                            for padrao in padroes_produtos:
                                match_produto = re.search(padrao, conteudo.lower())
                                if match_produto:
                                    termo_busca = match_produto.group(0).strip()
                                    produto_encontrado = self._buscar_produto_por_termo(termo_busca, todos_produtos)
                                    if produto_encontrado:
                                        fonte_produto = f"historico_padrao"
                                        print(f"🔍 Produto encontrado no histórico (padrão): '{termo_busca}' -> '{produto_encontrado['nome']}'")
                                        break
                        
                        if produto_encontrado:
                            break
                
                # 5. Se encontrou produto, gera resposta
                if produto_encontrado:
                    print(f"🔍 [IA] Detectada pergunta 'nele' sobre produto ({fonte_produto}): '{produto_encontrado['nome']}'")
                    
                    # Atualiza histórico
                    historico = dados.get('historico', [])
                    historico.append({"role": "user", "content": mensagem})
                    
                    # Gera resposta
                    resposta = await self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                    
                    # Salva resposta no histórico
                    historico.append({"role": "assistant", "content": resposta})
                    dados['historico'] = historico
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    return resposta
                
                # 6. Se não encontrou nenhum produto, pergunta qual produto
                resposta = "Qual produto você quer saber? Me fala o nome! 😊"
                
                # Salva no histórico
                historico = dados.get('historico', [])
                historico.append({"role": "user", "content": mensagem})
                historico.append({"role": "assistant", "content": resposta})
                dados['historico'] = historico
                self._salvar_estado_conversa(user_id, estado, dados)
                
                return resposta
        
        # Detecta perguntas do tipo "tem X?" ou "vocês tem X?" - usa busca inteligente
        padrao_tem = re.search(r'(?:tem|têm|vocês?\s+tem|vcs\s+tem)\s+([a-záàâãéêíóôõúç\-\s]+?)(?:\?|$|,|\.)', msg_lower)
        if padrao_tem:
            produto_pergunta = padrao_tem.group(1).strip()
            # Remove palavras genéricas
            palavras_ignorar = ['ai', 'aí', 'no', 'cardapio', 'menu', 'aqui', 'disponivel', 'disponível']
            produto_pergunta_limpo = ' '.join([p for p in produto_pergunta.split() if p.lower() not in palavras_ignorar])
            
            if produto_pergunta_limpo and len(produto_pergunta_limpo) > 2:
                print(f"🔍 [IA] Detectada pergunta 'tem X?': '{produto_pergunta_limpo}'")
                # Atualiza histórico com mensagem do usuário
                historico = dados.get('historico', [])
                historico.append({"role": "user", "content": mensagem})
                
                # Usa busca inteligente diretamente no banco
                produtos_encontrados = self._buscar_produtos_inteligente(produto_pergunta_limpo, limit=3)
                if produtos_encontrados:
                    # Se encontrou exatamente 1, mostra detalhes completos
                    if len(produtos_encontrados) == 1:
                        produto = produtos_encontrados[0]
                        # Salva o produto no contexto para perguntas futuras "o que vem nele?"
                        if 'pedido_contexto' not in dados:
                            dados['pedido_contexto'] = []
                        dados['pedido_contexto'].append({
                            'nome': produto['nome'],
                            'tipo': produto.get('tipo', 'produto'),
                            'id': produto.get('id')
                        })
                        dados['ultimo_produto_adicionado'] = produto['nome']
                        
                        # Gera resposta sobre o produto
                        resposta = await self._gerar_resposta_sobre_produto(user_id, produto, mensagem, dados)
                        
                        # Salva resposta no histórico
                        historico.append({"role": "assistant", "content": resposta})
                        dados['historico'] = historico
                        self._salvar_estado_conversa(user_id, estado, dados)
                        
                        return resposta
                    else:
                        # Se encontrou vários, lista os principais
                        resposta = f"Sim! Temos:\n\n"
                        for i, p in enumerate(produtos_encontrados[:3], 1):
                            resposta += f"{i}. *{p['nome']}* - R$ {p['preco']:.2f}\n"
                        resposta += "\nQual você quer saber mais? 😊"
                        
                        # Salva no histórico
                        historico.append({"role": "assistant", "content": resposta})
                        dados['historico'] = historico
                        self._salvar_estado_conversa(user_id, estado, dados)
                        
                        return resposta
                else:
                    resposta = f"Desculpa, não encontrei '{produto_pergunta_limpo}' no cardápio. Quer ver o que temos disponível? 😊"
                    
                    # Salva no histórico
                    historico.append({"role": "assistant", "content": resposta})
                    dados['historico'] = historico
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    return resposta
        
        # Detecta perguntas com nome de produto explícito
        quer_saber, nome_produto = detectar_pergunta_ingredientes(mensagem)
        if quer_saber and nome_produto:
            print(f"🔍 [IA] Detectada pergunta sobre ingredientes: '{nome_produto}' (mensagem original: '{mensagem}')")
            
            # Atualiza histórico
            historico = dados.get('historico', [])
            historico.append({"role": "user", "content": mensagem})
            
            # Usa busca inteligente diretamente no banco
            produtos_encontrados = self._buscar_produtos_inteligente(nome_produto, limit=1)
            if produtos_encontrados:
                produto_encontrado = produtos_encontrados[0]
                print(f"   ✅ Produto encontrado: {produto_encontrado.get('nome')} (tipo: {produto_encontrado.get('tipo')}, id: {produto_encontrado.get('id')})")
                
                # Passa a mensagem original para detectar que é pergunta sobre ingredientes
                resposta = await self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                
                # Salva resposta no histórico
                historico.append({"role": "assistant", "content": resposta})
                dados['historico'] = historico
                self._salvar_estado_conversa(user_id, estado, dados)
                
                return resposta
            else:
                # Fallback para busca na lista
                produto_encontrado = self._buscar_produto_por_termo(nome_produto, todos_produtos)
                if produto_encontrado:
                    print(f"   ✅ Produto encontrado na lista: {produto_encontrado.get('nome')} (tipo: {produto_encontrado.get('tipo')}, id: {produto_encontrado.get('id')})")
                    
                    # Passa a mensagem original para detectar que é pergunta sobre ingredientes
                    resposta = await self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                    
                    # Salva resposta no histórico
                    historico.append({"role": "assistant", "content": resposta})
                    dados['historico'] = historico
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    return resposta
                else:
                    resposta = f"Hmm, não encontrei o produto '{nome_produto}' no cardápio. Quer ver o cardápio completo? 😊"
                    
                    # Salva no histórico
                    historico.append({"role": "assistant", "content": resposta})
                    dados['historico'] = historico
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    return resposta
        
        # Detecta múltiplas ações na mensagem (ex: "Quero 2 xbacon. Um é sem tomate")
        acoes_detectadas = []
        msg_para_personalizacao = mensagem  # Inicializa com a mensagem original
        import re
        
        # 1. Tenta detectar adicionar produto
        resultado_adicionar = self._interpretar_intencao_regras(mensagem, todos_produtos, carrinho, dados)
        if resultado_adicionar:
            funcao_detectada = resultado_adicionar.get("funcao")
            if funcao_detectada == "adicionar_produto":
                acoes_detectadas.append(resultado_adicionar)
                # Remove a parte do produto da mensagem para buscar outras ações
                produto_busca = resultado_adicionar.get("params", {}).get("produto_busca", "")
                if produto_busca:
                    # Tenta remover o nome do produto da mensagem
                    padrao_produto = re.escape(produto_busca)
                    msg_para_personalizacao = re.sub(padrao_produto, '', mensagem, flags=re.IGNORECASE)
                    # Remove também padrões de quantidade e palavras de pedido
                    msg_para_personalizacao = re.sub(r'\d+\s*x?\s*', '', msg_para_personalizacao, flags=re.IGNORECASE)
                    msg_para_personalizacao = msg_para_personalizacao.replace('quero', '').replace('dois', '').replace('duas', '').replace('uma', '').replace('um', '').strip()
            elif funcao_detectada == "adicionar_produtos":
                itens = resultado_adicionar.get("params", {}).get("itens", [])
                for item in itens:
                    acoes_detectadas.append({
                        "funcao": "adicionar_produto",
                        "params": {
                            "produto_busca": item.get("produto_busca", ""),
                            "produto_busca_alt": item.get("produto_busca_alt", ""),
                            "prefer_alt": bool(item.get("prefer_alt", False)),
                            "quantidade": item.get("quantidade", 1)
                        }
                    })
        
        # 2. Detecta personalização na mensagem (original ou sem o produto)
        if re.search(r'sem\s+(\w+)', msg_para_personalizacao, re.IGNORECASE):
            match = re.search(r'sem\s+(\w+)', msg_para_personalizacao, re.IGNORECASE)
            if match:
                acoes_detectadas.append({
                    "funcao": "personalizar_produto",
                    "params": {"acao": "remover_ingrediente", "item": match.group(1)}
                })
        
        if re.search(r'(mais|extra|adiciona)\s+(\w+)', msg_para_personalizacao, re.IGNORECASE):
            match = re.search(r'(mais|extra|adiciona)\s+(\w+)', msg_para_personalizacao, re.IGNORECASE)
            if match:
                acoes_detectadas.append({
                    "funcao": "personalizar_produto",
                    "params": {"acao": "adicionar_extra", "item": match.group(2)}
                })
        
        # Se detectou múltiplas ações, processa em sequência
        if len(acoes_detectadas) > 1:
            print(f"🎯 Detectadas {len(acoes_detectadas)} ações na mensagem: {[a.get('funcao') for a in acoes_detectadas]}")
            
            historico = dados.get('historico', [])
            historico.append({"role": "user", "content": mensagem})
            dados['historico'] = historico
            
            mensagens_resposta = []
            
            # Processa cada ação em sequência
            for acao in acoes_detectadas:
                funcao = acao.get("funcao")
                params = acao.get("params", {})
                
                if funcao == "adicionar_produto":
                    produto_busca = params.get("produto_busca", "")
                    produto_busca_alt = params.get("produto_busca_alt", "")
                    prefer_alt = bool(params.get("prefer_alt", False))
                    quantidade = params.get("quantidade", 1)
                    personalizacao = params.get("personalizacao")  # Pode ter personalizacao junto
                    produto = self._resolver_produto_para_preco(
                        produto_busca, produto_busca_alt, prefer_alt, todos_produtos
                    )
                    
                    if produto:
                        # Adiciona ao pedido_contexto no modo conversacional
                        pedido_contexto = dados.get('pedido_contexto', [])
                        
                        # Prepara removidos e adicionais baseado na personalização
                        removidos = []
                        adicionais = []
                        if personalizacao:
                            acao_personalizar = personalizacao.get("acao", "")
                            item_personalizar = personalizacao.get("item", "")
                            if acao_personalizar == "remover_ingrediente" and item_personalizar:
                                removidos.append(item_personalizar)
                            elif acao_personalizar == "adicionar_extra" and item_personalizar:
                                adicionais.append(item_personalizar)
                        
                        self._adicionar_ao_carrinho(user_id, dados, produto, quantidade)
                        for _ in range(quantidade):
                            novo_item = {
                                'id': str(produto['id']),
                                'nome': produto['nome'],
                                'preco': produto['preco'],
                                'quantidade': 1,
                                'removidos': removidos.copy(),  # Usa cópia para não compartilhar referência
                                'adicionais': adicionais.copy(),
                                'preco_adicionais': 0.0
                            }
                            pedido_contexto.append(novo_item)
                        
                        dados['pedido_contexto'] = pedido_contexto
                        mensagem_item = f"✅ Adicionei {quantidade}x *{produto['nome']}*"
                        if removidos:
                            mensagem_item += f" SEM {', '.join(removidos)}"
                        if adicionais:
                            mensagem_item += f" COM {', '.join(adicionais)}"
                        mensagem_item += " ao pedido!"
                        mensagens_resposta.append(mensagem_item)
                
                elif funcao == "personalizar_produto":
                    acao_personalizar = params.get("acao", "")
                    item_nome = params.get("item", "")
                    produto_busca = params.get("produto_busca", "")
                    
                    sucesso, msg_personalizacao = self._personalizar_item_carrinho(
                        dados, acao_personalizar, item_nome, produto_busca
                    )
                    if sucesso:
                        mensagens_resposta.append(msg_personalizacao)
            
            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
            
            if mensagens_resposta:
                resposta_final = "\n\n".join(mensagens_resposta)
                resposta_final += "\n\nMais alguma coisa? 😊"
                return resposta_final
        
        # Processamento normal de uma única ação
        resultado_regras = self._interpretar_intencao_regras(mensagem, todos_produtos, carrinho, dados)
        
        if resultado_regras:
            funcao = resultado_regras.get("funcao")
            params = resultado_regras.get("params", {})
            print(f"🎯 Regras detectaram no modo conversacional: {funcao}({params})")
            
            # Se detectou uma função específica (não apenas "conversar"), executa ela
            if funcao != "conversar":
                # Atualiza histórico
                historico = dados.get('historico', [])
                historico.append({"role": "user", "content": mensagem})
                dados['historico'] = historico
                
                # Executa a função detectada
                if funcao == "informar_sobre_produto":
                    produto_busca = params.get("produto_busca", "")
                    pergunta = params.get("pergunta", "")
                    produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)
                    if produto:
                        # Memoriza o último produto mencionado/consultado
                        try:
                            dados["ultimo_produto_mencionado"] = {
                                "nome": produto.get("nome"),
                                "tipo": produto.get("tipo", "produto"),
                                "id": produto.get("id"),
                            }
                        except Exception:
                            pass
                        return await self._gerar_resposta_sobre_produto(user_id, produto, pergunta, dados)
                    else:
                        return f"❌ Não encontrei *{produto_busca}* no cardápio 😔\n\nQuer que eu mostre o que temos disponível? 😊"
                elif funcao == "informar_sobre_produtos":
                    itens = params.get("itens", [])
                    if itens:
                        resposta_preco = self._gerar_resposta_preco_itens(user_id, dados, itens, todos_produtos)
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        return resposta_preco
                    return "Qual produto você quer saber o preço?"
                elif funcao == "adicionar_produto":
                    produto_busca = params.get("produto_busca", "")
                    produto_busca_alt = params.get("produto_busca_alt", "")
                    prefer_alt = bool(params.get("prefer_alt", False))
                    quantidade = params.get("quantidade", 1)
                    produto = self._resolver_produto_para_preco(
                        produto_busca, produto_busca_alt, prefer_alt, todos_produtos
                    )
                    if not produto:
                        return f"❌ Não encontrei *{produto_busca}* no cardápio 😔\n\nQuer que eu mostre o que temos disponível? 😊"

                    pedido_contexto = dados.get('pedido_contexto', [])
                    self._adicionar_ao_carrinho(user_id, dados, produto, quantidade)
                    for _ in range(quantidade):
                        pedido_contexto.append({
                            'id': str(produto['id']),
                            'nome': produto['nome'],
                            'preco': produto['preco'],
                            'quantidade': 1,
                            'removidos': [],
                            'adicionais': [],
                            'preco_adicionais': 0.0
                        })
                    dados['pedido_contexto'] = pedido_contexto
                    dados['ultimo_produto_adicionado'] = produto['nome']
                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    return f"✅ Adicionei {quantidade}x *{produto['nome']}* ao pedido!\n\nMais alguma coisa? 😊"
                elif funcao == "adicionar_produtos":
                    itens = params.get("itens", [])
                    if not itens:
                        return "O que você gostaria de pedir?"

                    pedido_contexto = dados.get('pedido_contexto', [])
                    mensagens_resposta = []
                    for item in itens:
                        produto_busca = item.get("produto_busca", "")
                        produto_busca_alt = item.get("produto_busca_alt", "")
                        prefer_alt = bool(item.get("prefer_alt", False))
                        quantidade = int(item.get("quantidade", 1) or 1)
                        produto = self._resolver_produto_para_preco(
                            produto_busca, produto_busca_alt, prefer_alt, todos_produtos
                        )
                        if not produto:
                            mensagens_resposta.append(f"❌ Não encontrei *{produto_busca}* no cardápio 😔")
                            continue

                        self._adicionar_ao_carrinho(user_id, dados, produto, quantidade)
                        for _ in range(quantidade):
                            pedido_contexto.append({
                                'id': str(produto['id']),
                                'nome': produto['nome'],
                                'preco': produto['preco'],
                                'quantidade': 1,
                                'removidos': [],
                                'adicionais': [],
                                'preco_adicionais': 0.0
                            })
                        mensagens_resposta.append(f"✅ Adicionei {quantidade}x *{produto['nome']}* ao pedido!")
                        dados['ultimo_produto_adicionado'] = produto['nome']

                    dados['pedido_contexto'] = pedido_contexto
                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    resposta_final = "\n\n".join(mensagens_resposta) if mensagens_resposta else "O que você gostaria de pedir?"
                    resposta_final += "\n\nMais alguma coisa? 😊"
                    return resposta_final
                elif funcao == "ver_cardapio":
                    # VERIFICA SE ACEITA PEDIDOS PELO WHATSAPP
                    config = self._get_chatbot_config()
                    if config and not config.aceita_pedidos_whatsapp:
                        # Não aceita pedidos - retorna link do cardápio em vez de listar produtos
                        try:
                            empresa_query = text("""
                                SELECT nome, cardapio_link
                                FROM cadastros.empresas
                                WHERE id = :empresa_id
                            """)
                            result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                            empresa = result.fetchone()
                            link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                        except Exception as e:
                            print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                            link_cardapio = LINK_CARDAPIO
                        
                        # Retorna mensagem com link do cardápio
                        if config.mensagem_redirecionamento:
                            resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                        else:
                            resposta = f"📲 Para ver nosso cardápio completo e fazer seu pedido, acesse pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                        return resposta
                    
                    # Se aceita pedidos, mostra a lista normalmente
                    pedido_contexto = dados.get('pedido_contexto', [])
                    return self._gerar_lista_produtos(todos_produtos, pedido_contexto)
                elif funcao == "ver_carrinho":
                    if carrinho:
                        msg = self._formatar_carrinho(carrinho)
                        msg += "\n\nQuer mais algo ou posso fechar?"
                        return msg
                    else:
                        return "Carrinho vazio ainda! O que vai ser hoje?"
                elif funcao == "iniciar_novo_pedido":
                    # Verifica se há carrinho em aberto
                    carrinho_aberto = self._verificar_carrinho_aberto(user_id)
                    
                    if carrinho_aberto:
                        # Há carrinho aberto - pergunta confirmação antes de limpar
                        dados['aguardando_confirmacao_cancelamento_carrinho'] = True
                        dados['carrinho_aberto_tratado'] = True
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        return self._formatar_mensagem_carrinho_aberto(carrinho_aberto)
                    else:
                        # Não há carrinho aberto - apenas reinicia o contexto
                        dados['pedido_contexto'] = []
                        dados['ultimo_produto_adicionado'] = None
                        dados['ultimo_produto_mencionado'] = None
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        return "✅ Perfeito! Vamos começar um novo pedido! 😊\n\nO que você gostaria de pedir hoje?"
                elif funcao == "ver_combos":
                    return self.ingredientes_service.formatar_combos_para_chat()
                elif funcao == "ver_adicionais":
                    produto_busca = params.get("produto_busca", "")
                    if not produto_busca:
                        produto_busca = dados.get('ultimo_produto_adicionado', '')
                    if not produto_busca and carrinho:
                        produto_busca = carrinho[-1]['nome']
                    
                    if produto_busca:
                        complementos = self.ingredientes_service.buscar_complementos_por_nome_receita(produto_busca)
                        if complementos:
                            msg = self.ingredientes_service.formatar_complementos_para_chat(complementos, produto_busca)
                            msg += "\n\nPara adicionar, diga o nome do item 😊"
                            return msg
                    
                    todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
                    if todos_adicionais:
                        msg = "➕ *Adicionais disponíveis:*\n\n"
                        for add in todos_adicionais:
                            msg += f"• {add['nome']} - +R$ {add['preco']:.2f}\n"
                        msg += "\nPara adicionar, diga o nome do item 😊"
                        return msg
                    else:
                        return "No momento não temos adicionais extras disponíveis 😅"
                elif funcao == "calcular_taxa_entrega":
                    # Extrai endereço usando IA
                    mensagem_original = params.get("mensagem_original", "")
                    endereco = params.get("endereco", "")
                    
                    # Se não veio endereço direto, extrai da mensagem original com IA
                    if not endereco and mensagem_original:
                        endereco = await self._extrair_endereco_com_ia(mensagem_original)
                    
                    return await self._calcular_e_responder_taxa_entrega(user_id, endereco, dados)
                elif funcao == "informar_sobre_estabelecimento":
                    tipo_pergunta = params.get("tipo_pergunta", "ambos")
                    empresas = self._buscar_empresas_ativas()
                    
                    if not empresas:
                        return "❌ Não foi possível obter informações do estabelecimento no momento. 😔"
                    
                    # Busca empresa atual (se não estiver na lista, busca do banco)
                    empresa_atual = None
                    for emp in empresas:
                        if emp['id'] == self.empresa_id:
                            empresa_atual = emp
                            break
                    
                    # Se não encontrou na lista, busca diretamente do banco
                    if not empresa_atual:
                        try:
                            result = self.db.execute(text("""
                                SELECT id, nome, bairro, cidade, estado, logradouro, numero, 
                                       complemento, horarios_funcionamento
                                FROM cadastros.empresas
                                WHERE id = :empresa_id
                            """), {"empresa_id": self.empresa_id})
                            row = result.fetchone()
                            if row:
                                empresa_atual = {
                                    'id': row[0],
                                    'nome': row[1],
                                    'bairro': row[2],
                                    'cidade': row[3],
                                    'estado': row[4],
                                    'logradouro': row[5],
                                    'numero': row[6],
                                    'complemento': row[7],
                                    'horarios_funcionamento': row[8]
                                }
                                # Adiciona à lista para usar na formatação
                                empresas.append(empresa_atual)
                        except Exception as e:
                            print(f"❌ Erro ao buscar empresa atual: {e}")
                    
                    resposta = ""
                    
                    if tipo_pergunta in ["horario", "ambos"]:
                        if empresa_atual:
                            horarios = self._formatar_horarios_funcionamento(empresa_atual.get('horarios_funcionamento'))
                            resposta += horarios + "\n\n"
                        else:
                            resposta += "Horários de funcionamento não disponíveis.\n\n"
                    
                    if tipo_pergunta in ["localizacao", "ambos"]:
                        localizacao = self._formatar_localizacao_empresas(empresas, self.empresa_id)
                        resposta += localizacao
                    
                    return resposta
                elif funcao == "cancelar_pedido":
                    # Cliente quer cancelar um pedido
                    # Verifica se há pedido aberto (passado como parâmetro)
                    if pedido_aberto:
                        pedido_id = pedido_aberto.get('pedido_id')
                        if pedido_id:
                            sucesso, mensagem_resultado = await self._cancelar_pedido(pedido_id=pedido_id, user_id=user_id)
                            if sucesso:
                                # Limpa o carrinho também
                                dados['carrinho'] = []
                                dados['pedido_contexto'] = []
                                dados.pop('pedido_aberto_id', None)
                                dados.pop('pedido_aberto_tratado', None)
                                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                                
                                # Limpa o carrinho temporário do schema chatbot
                                try:
                                    service = self._get_carrinho_service()
                                    service.limpar_carrinho(user_id, self.empresa_id)
                                except Exception as e:
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.error(f"Erro ao limpar carrinho após cancelamento: {e}", exc_info=True)
                                
                                return f"✅ {mensagem_resultado}\n\nComo posso te ajudar agora? 😊"
                            else:
                                return f"❌ {mensagem_resultado}\n\nComo posso te ajudar? 😊"
                    
                    # Verifica se há carrinho com itens (pedido em andamento)
                    carrinho = dados.get('carrinho', [])
                    if carrinho and len(carrinho) > 0:
                        # Limpa o carrinho
                        dados['carrinho'] = []
                        dados['pedido_contexto'] = []
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        
                        # Limpa o carrinho temporário do schema chatbot
                        try:
                            service = self._get_carrinho_service()
                            service.limpar_carrinho(user_id, self.empresa_id)
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Erro ao limpar carrinho após cancelamento: {e}", exc_info=True)
                        
                        return "✅ Pedido cancelado! Limpei o carrinho.\n\nComo posso te ajudar agora? 😊"
                    
                    # Não há pedido para cancelar
                    return "Não há nenhum pedido em aberto para cancelar. 😊\n\nComo posso te ajudar?"
                elif funcao == "iniciar_novo_pedido":
                    # Verifica se há carrinho em aberto
                    carrinho_aberto = self._verificar_carrinho_aberto(user_id)
                    
                    if carrinho_aberto:
                        # Há carrinho aberto - pergunta confirmação antes de limpar
                        dados['aguardando_confirmacao_cancelamento_carrinho'] = True
                        dados['carrinho_aberto_tratado'] = True
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        return self._formatar_mensagem_carrinho_aberto(carrinho_aberto)
                    else:
                        # Não há carrinho aberto - apenas reinicia o contexto
                        dados['pedido_contexto'] = []
                        dados['ultimo_produto_adicionado'] = None
                        dados['ultimo_produto_mencionado'] = None
                        dados.pop('pedido_aberto_id', None)
                        dados.pop('pedido_aberto_tratado', None)
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        return "✅ Perfeito! Vamos começar um novo pedido! 😊\n\nO que você gostaria de pedir hoje?"
                elif funcao == "chamar_atendente":
                    # Cliente quer chamar atendente humano
                    # Envia notificação para a empresa
                    await self._enviar_notificacao_chamar_atendente(user_id, dados)
                    return "✅ *Solicitação enviada!*\n\nNossa equipe foi notificada e entrará em contato com você em breve.\n\nEnquanto isso, posso te ajudar com alguma dúvida? 😊"
                elif funcao == "informar_sobre_estabelecimento":
                    if tipo_pergunta in ["localizacao", "ambos"]:
                        localizacao = self._formatar_localizacao_empresas(empresas, self.empresa_id)
                        resposta += localizacao
                    
                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    return resposta.strip()
                elif funcao == "chamar_atendente":
                    # Cliente quer chamar atendente humano
                    # Envia notificação para a empresa
                    await self._enviar_notificacao_chamar_atendente(user_id, dados)
                    return "✅ *Solicitação enviada!*\n\nNossa equipe foi notificada e entrará em contato com você em breve.\n\nEnquanto isso, posso te ajudar com alguma dúvida? 😊"
                elif funcao == "personalizar_produto":
                    acao = params.get("acao", "")
                    item_nome = params.get("item", "")
                    produto_busca = params.get("produto_busca", "")
                    
                    print(f"🔧 Personalizando no modo conversacional: acao={acao}, item={item_nome}, produto={produto_busca}")
                    
                    if not acao or not item_nome:
                        return "Não entendi a personalização 😅 Tenta de novo!"
                    
                    sucesso, mensagem_resposta = self._personalizar_item_carrinho(
                        dados, acao, item_nome, produto_busca
                    )
                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    
                    if sucesso:
                        mensagem_resposta += "\n\nMais alguma coisa? 😊"
                    return mensagem_resposta

        # Atualiza histórico
        historico = dados.get('historico', [])
        historico.append({"role": "user", "content": mensagem})

        # Busca dados do cardápio
        pedido_contexto = dados.get('pedido_contexto', [])
        carrinho = dados.get('carrinho', [])

        # Verifica se cliente está pedindo cardápio - responde direto sem IA
        msg_lower = mensagem.lower().strip()
        if re.search(r'(cardapio|cardápio|menu)', msg_lower) and re.search(r'(qual|ver|mostrar|quero|me\s*(da|dá|mostra)|^cardapio$|^menu$)', msg_lower):
            dados['historico'] = historico
            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
            return self._gerar_lista_produtos(todos_produtos, pedido_contexto)

        # Também aceita só "cardapio" ou "menu"
        if msg_lower in ['cardapio', 'cardápio', 'menu']:
            dados['historico'] = historico
            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
            return self._gerar_lista_produtos(todos_produtos, pedido_contexto)

        # VERIFICA SE ESTÁ AGUARDANDO SELEÇÃO DE COMPLEMENTOS
        aguardando_complemento = dados.get('aguardando_complemento', False)
        complementos_disponiveis = dados.get('complementos_disponiveis', [])

        # Monta cardápio formatado
        cardapio_texto = self._formatar_cardapio_para_ia(todos_produtos)

        # Monta contexto do pedido atual
        pedido_atual = ""
        if pedido_contexto:
            pedido_atual = "\n📝 PEDIDO ANOTADO ATÉ AGORA:\n"
            total = 0
            for item in pedido_contexto:
                preco_item = item.get('preco', 0) * item.get('quantidade', 1)
                total += preco_item
                pedido_atual += f"- {item.get('quantidade', 1)}x {item['nome']} - R$ {preco_item:.2f}"
                if item.get('removidos'):
                    pedido_atual += f" (SEM: {', '.join(item['removidos'])})"
                if item.get('adicionais'):
                    pedido_atual += f" (COM: {', '.join(item['adicionais'])})"
                pedido_atual += "\n"
            pedido_atual += f"💰 Total parcial: R$ {total:.2f}\n"
        else:
            pedido_atual = "\n📝 PEDIDO: Nenhum item anotado ainda.\n"

        # Monta seção de complementos se estiver aguardando seleção
        complementos_texto = ""
        if aguardando_complemento and complementos_disponiveis and pedido_contexto:
            ultimo_item = pedido_contexto[-1]
            complementos_texto = f"\n\n🔔 ATENÇÃO: O cliente acabou de pedir '{ultimo_item['nome']}' e você ofereceu os complementos abaixo. Agora analise a resposta do cliente:\n"
            complementos_texto += "COMPLEMENTOS DISPONÍVEIS:\n"
            for comp in complementos_disponiveis:
                obrig = "OBRIGATÓRIO" if comp.get('obrigatorio') else "opcional"
                minimo = comp.get('minimo_itens', 0)
                maximo = comp.get('maximo_itens', 0)
                complementos_texto += f"\n• {comp.get('nome', '')} ({obrig}, min: {minimo}, max: {maximo}):\n"
                for adicional in comp.get('adicionais', []):
                    preco = adicional.get('preco', 0)
                    preco_str = f" - R$ {preco:.2f}" if preco > 0 else " - grátis"
                    complementos_texto += f"  - {adicional.get('nome', '')}{preco_str}\n"
            complementos_texto += "\nSe o cliente escolher complementos, use acao 'selecionar_complementos' com os nomes EXATOS dos itens escolhidos."
            complementos_texto += "\nSe o cliente não quiser nenhum, use acao 'pular_complementos'."

        # FASE 2 (RAG): Contexto curto do catálogo baseado na mensagem (para dúvidas abertas)
        contexto_rag = self._buscar_contexto_catalogo_rag(mensagem, limit=10)
        contexto_rag_txt = ""
        if contexto_rag:
            contexto_rag_txt = f"\n\nITENS RELEVANTES DO CATÁLOGO (RAG):\n{contexto_rag}\n"

        # FASE 3: Resolver referências na mensagem ("esse", "o último", "o de frango")
        mensagem_resolvida = self._resolver_referencias_na_mensagem(mensagem, pedido_contexto, carrinho, dados)
        
        # FASE 3: Memória curta resumida - contexto do pedido de forma mais inteligente
        contexto_pedido_resumido = self._resumir_contexto_pedido(pedido_contexto, carrinho)

        # Prompt do sistema para IA conversacional
        system_prompt = f"""Você é um atendente de delivery simpático e prestativo. Seu nome é Assistente Virtual.

SUAS RESPONSABILIDADES:
1. Conversar naturalmente com o cliente
2. Tirar dúvidas sobre produtos (ingredientes, preços, tamanhos)
3. Anotar os pedidos do cliente mentalmente
4. Quando o cliente quiser finalizar, perguntar se pode prosseguir para entrega

CARDÁPIO COMPLETO:
{cardapio_texto}
{contexto_rag_txt}

{contexto_pedido_resumido}
{complementos_texto}

REGRAS IMPORTANTES:
- Seja DIRETO e objetivo. NÃO peça confirmação do pedido, apenas anote e pergunte se quer mais algo
- Quando o cliente PEDIR produtos, ANOTE IMEDIATAMENTE e diga "Anotado! [itens]. Quer mais algo?"
- NÃO pergunte "certo?", "é isso?", "confirma?" - apenas anote e siga em frente
- Quando o cliente PERGUNTAR sobre um produto (ingredientes, preço), responda a dúvida SEM adicionar ao pedido
- Se o cliente quiser personalizar (sem cebola, com bacon extra), anote a personalização
- Quando o cliente disser "só isso", "não quero mais nada", "pode fechar", use acao "prosseguir_entrega"
- NÃO invente produtos ou preços, use apenas o que está no cardápio
- Respostas CURTAS (máximo 2-3 linhas)
- IMPORTANTE: Use SEMPRE o nome EXATO do produto como está no cardápio (ex: "xbacon" = "X-Bacon", "cocacola" = "Coca-Cola")

EXEMPLOS DE COMPORTAMENTO CORRETO:
- Cliente: "quero 1 pizza calabresa e 1 coca" → "Anotado! 1 Pizza Calabresa e 1 Coca-Cola. Quer mais algo? 😊" (acao: adicionar)
- Cliente: "o que tem na pizza?" → [responde ingredientes] (acao: nenhuma)
- Cliente: "só isso" → "Perfeito! Podemos prosseguir para a entrega? 🚗" (acao: prosseguir_entrega)
- Cliente: "sim" (após perguntar se quer finalizar) → use acao "prosseguir_entrega"

FORMATO DE RESPOSTA - SEMPRE RETORNE JSON VÁLIDO, SEM EXCEÇÃO:
{{
    "resposta": "sua mensagem curta para o cliente",
    "acao": "nenhuma" | "adicionar" | "remover" | "prosseguir_entrega" | "selecionar_complementos" | "pular_complementos",
    "itens": [
        {{
            "nome": "nome exato do produto do cardápio",
            "quantidade": 1,
            "removidos": [],
            "adicionais": []
        }}
    ],
    "complementos_selecionados": ["nome exato do complemento escolhido"]
}}

REGRAS CRÍTICAS:
1. SEMPRE retorne APENAS JSON válido, nunca texto puro
2. Se cliente pedir MÚLTIPLOS produtos: coloque TODOS no array "itens"
3. Se cliente PERSONALIZAR (tirar/adicionar ingrediente): use "acao": "adicionar" com o item e removidos/adicionais preenchidos
4. Se não houver ação: use "acao": "nenhuma" e "itens": []
5. OBRIGATÓRIO: Quando acao for "adicionar", o array "itens" NUNCA pode estar vazio! Sempre inclua os produtos!
6. Reconheça pedidos mesmo sem "quero" - ex: "1 pizza", "2 x-bacon", "uma coca" são pedidos válidos

EXEMPLOS DE PEDIDOS (todos são acao: adicionar com itens preenchidos):
- "1 pizza pepperoni" → {{"resposta": "Anotado! 1 Pizza Pepperoni. Quer mais algo?", "acao": "adicionar", "itens": [{{"nome": "Pizza Pepperoni", "quantidade": 1, "removidos": [], "adicionais": []}}]}}
- "2 xbacon" → {{"resposta": "Anotado! 2 X-Bacon. Quer mais algo?", "acao": "adicionar", "itens": [{{"nome": "X-Bacon", "quantidade": 2, "removidos": [], "adicionais": []}}]}}
- "uma coca" → {{"resposta": "Anotado! 1 Coca-Cola. Quer mais algo?", "acao": "adicionar", "itens": [{{"nome": "Coca-Cola", "quantidade": 1, "removidos": [], "adicionais": []}}]}}

EXEMPLOS DE PERSONALIZAÇÃO:
- Cliente: "tira o molho da pizza" → {{"resposta": "Anotado! Pizza sem molho.", "acao": "adicionar", "itens": [{{"nome": "Pizza Calabresa", "quantidade": 1, "removidos": ["Molho de Tomate"], "adicionais": []}}]}}
- Cliente: "quero pizza sem cebola" → {{"resposta": "Pizza sem cebola, anotado!", "acao": "adicionar", "itens": [{{"nome": "Pizza Calabresa", "quantidade": 1, "removidos": ["Cebola"], "adicionais": []}}]}}

EXEMPLOS DE COMPLEMENTOS (quando tiver complementos disponíveis):
- Cliente: "maionese e queijo extra" → {{"resposta": "Adicionei maionese e queijo extra! Quer mais algo?", "acao": "selecionar_complementos", "itens": [], "complementos_selecionados": ["Maionese 30 ml", "Queijo Extra"]}}
- Cliente: "não quero nada" → {{"resposta": "Ok, sem adicionais! Quer mais algo?", "acao": "pular_complementos", "itens": [], "complementos_selecionados": []}}
- Cliente: "bacon" → {{"resposta": "Bacon adicionado! Mais alguma coisa?", "acao": "selecionar_complementos", "itens": [], "complementos_selecionados": ["Bacon Extra"]}}
- Cliente: "2 maionese" → {{"resposta": "Anotado! 2x Maionese. Quer mais algo?", "acao": "selecionar_complementos", "itens": [], "complementos_selecionados": ["2x Maionese 30 ml"]}}
- Cliente: "quero 3 queijo extra" → {{"resposta": "3x Queijo Extra adicionado!", "acao": "selecionar_complementos", "itens": [], "complementos_selecionados": ["3x Queijo Extra"]}}

REGRA PARA COMPLEMENTOS:
- Quando tiver COMPLEMENTOS DISPONÍVEIS listados acima e o cliente mencionar algum deles, use acao "selecionar_complementos" com os nomes EXATOS da lista
- Se o cliente disser "não", "nenhum", "só isso" para os complementos, use acao "pular_complementos"
- complementos_selecionados deve SEMPRE ter os nomes EXATOS como aparecem na lista de COMPLEMENTOS DISPONÍVEIS
- IMPORTANTE: Se o cliente especificar QUANTIDADE (ex: "2 maionese", "3 queijo extra"), inclua a quantidade no formato "Nx Nome" (ex: "2x Maionese 30 ml")"""

        # Injeta guardrails anti-alucinação (sem mudar o prompt funcional existente)
        system_prompt = build_system_prompt(system_prompt, require_json_object=True)

        # FASE 3: Memória curta resumida - resumir histórico quando muito longo
        historico_resumido = self._resumir_historico_para_ia(historico, max_mensagens=8)
        
        # Monta mensagens para a API
        messages = [{"role": "system", "content": system_prompt}]

        # Adiciona histórico resumido
        for msg in historico_resumido:
            messages.append(msg)
        
        # FASE 3: Adiciona mensagem resolvida (com referências resolvidas) como última mensagem
        # Se a última mensagem do histórico já é a mensagem atual, substitui pela resolvida
        if messages and messages[-1].get("role") == "user" and messages[-1].get("content") == mensagem:
            messages[-1]["content"] = mensagem_resolvida
        else:
            # Se não está no histórico, adiciona
            messages.append({"role": "user", "content": mensagem_resolvida})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "temperature": clamp_temperature(0.7),
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},  # Força resposta JSON
                }

                # Verifica se a chave API está configurada
                if not GROQ_API_KEY or not GROQ_API_KEY.strip():
                    print("⚠️ GROQ_API_KEY não configurada - usando fallback inteligente")
                    raise ValueError("GROQ_API_KEY não configurada")
                
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    resposta_ia = result["choices"][0]["message"]["content"].strip()

                    # Tenta parsear JSON
                    try:
                        ALLOWED_ACOES = (
                            "nenhuma",
                            "adicionar",
                            "remover",
                            "prosseguir_entrega",
                            "selecionar_complementos",
                            "pular_complementos",
                        )

                        # 1) Extrai JSON (mesmo que venha com lixo antes/depois)
                        resposta_json, _json_str = extract_first_json_object(resposta_ia)

                        # 2) Se falhou ou veio inválido, tenta 1 "repair" controlado (JSON-only)
                        async def _try_repair_json(bad_text: str) -> Optional[Dict[str, Any]]:
                            try:
                                repair_messages = [
                                    {"role": "system", "content": make_json_repair_prompt(allowed_actions=ALLOWED_ACOES)},
                                    {
                                        "role": "user",
                                        "content": (
                                            "Corrija para o formato esperado.\n\n"
                                            f"Mensagem do cliente: {mensagem_resolvida}\n\n"
                                            "Texto inválido/ambíguo do modelo:\n"
                                            f"{bad_text}"
                                        ),
                                    },
                                ]
                                repair_payload = {
                                    "model": MODEL_NAME,
                                    "messages": repair_messages,
                                    "temperature": 0.0,
                                    "max_tokens": 350,
                                    "response_format": {"type": "json_object"},
                                }
                                repair_resp = await client.post(GROQ_API_URL, json=repair_payload, headers=headers)
                                if repair_resp.status_code != 200:
                                    return None
                                repair_result = repair_resp.json()
                                repair_text = repair_result["choices"][0]["message"]["content"].strip()
                                repaired, _ = extract_first_json_object(repair_text)
                                return repaired
                            except Exception:
                                return None

                        if not isinstance(resposta_json, dict):
                            repaired = await _try_repair_json(resposta_ia)
                            if isinstance(repaired, dict):
                                resposta_json = repaired

                        if isinstance(resposta_json, dict):
                            ok, motivo = validate_action_json(resposta_json, allowed_actions=ALLOWED_ACOES)
                            if not ok:
                                print(f"⚠️ JSON inválido ({motivo}) — tentando corrigir")
                                repaired = await _try_repair_json(resposta_ia)
                                if isinstance(repaired, dict):
                                    resposta_json = repaired

                        # Gate final: se ainda não for JSON válido, cai no fallback atual
                        if not isinstance(resposta_json, dict):
                            raise json.JSONDecodeError("Resposta não é um objeto JSON", resposta_ia, 0)
                        ok_final, motivo_final = validate_action_json(resposta_json, allowed_actions=ALLOWED_ACOES)
                        if not ok_final:
                            raise json.JSONDecodeError(f"JSON inválido: {motivo_final}", resposta_ia, 0)

                        resposta_texto = resposta_json.get("resposta", resposta_ia)
                        acao = resposta_json.get("acao", "nenhuma")
                        print(f"🎯 Ação: {acao}")

                        # Suporta tanto "itens" (array) quanto "item" (singular) para compatibilidade
                        itens = resposta_json.get("itens", [])
                        item_singular = resposta_json.get("item")
                        if item_singular and not itens:
                            itens = [item_singular]
                        print(f"📦 Itens recebidos: {itens}")

                        # VERIFICA SE ACEITA PEDIDOS ANTES DE PROCESSAR AÇÃO DE ADICIONAR
                        config = self._get_chatbot_config()
                        if config and not config.aceita_pedidos_whatsapp and acao == "adicionar":
                            # Busca link do cardápio da empresa
                            try:
                                empresa_query = text("""
                                    SELECT nome, cardapio_link
                                    FROM cadastros.empresas
                                    WHERE id = :empresa_id
                                """)
                                result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                                empresa = result.fetchone()
                                link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                            except Exception as e:
                                print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                                link_cardapio = LINK_CARDAPIO
                            
                            # Retorna mensagem de redirecionamento
                            if config.mensagem_redirecionamento:
                                resposta_redir = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                            else:
                                resposta_redir = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                            
                            # Salva no histórico e retorna
                            historico.append({"role": "assistant", "content": resposta_redir})
                            dados['historico'] = historico
                            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                            return resposta_redir

                        # Processa ação
                        mostrar_resumo = False
                        if acao == "adicionar" and itens:
                            # Processa cada item da lista
                            for item in itens:
                                # Busca produto no cardápio para pegar preço correto
                                produto_encontrado = self._buscar_produto_por_termo(item.get("nome", ""), todos_produtos)
                                if produto_encontrado:
                                    nome_produto = produto_encontrado["nome"]
                                    removidos_raw = item.get("removidos", [])
                                    adicionais_raw = item.get("adicionais", [])

                                    # Normaliza removidos - LLM pode retornar listas aninhadas
                                    removidos = []
                                    for r in removidos_raw:
                                        if isinstance(r, list):
                                            removidos.extend([str(x) for x in r])
                                        else:
                                            removidos.append(str(r))

                                    # Normaliza adicionais - LLM pode retornar listas aninhadas
                                    adicionais = []
                                    for a in adicionais_raw:
                                        if isinstance(a, list):
                                            # Flatten lista aninhada
                                            adicionais.extend([str(x) for x in a])
                                        else:
                                            adicionais.append(str(a))

                                    # Verifica se o item já existe no contexto
                                    item_existente = None
                                    for p in pedido_contexto:
                                        if p["nome"].lower() == nome_produto.lower():
                                            item_existente = p
                                            break

                                    if item_existente:
                                        # Atualiza item existente (personalização ou quantidade)
                                        # IMPORTANTE: Manter adicionais, preco_adicionais e complementos_checkout existentes!
                                        if removidos:
                                            # Adiciona aos removidos existentes (não substitui)
                                            removidos_existentes = item_existente.get("removidos", [])
                                            for r in removidos:
                                                if r not in removidos_existentes:
                                                    removidos_existentes.append(r)
                                            item_existente["removidos"] = removidos_existentes

                                        # PRESERVA adicionais, preco_adicionais e complementos_checkout existentes
                                        adicionais_existentes = item_existente.get("adicionais", [])
                                        preco_existente = item_existente.get("preco_adicionais", 0.0)
                                        checkout_existente = item_existente.get("complementos_checkout", [])

                                        # Verifica se há novos adicionais a adicionar
                                        if adicionais:
                                            nomes_existentes = set(a.lower() for a in adicionais_existentes)
                                            nomes_llm = set(a.lower() for a in adicionais)

                                            # Encontra apenas os NOVOS (que não existem ainda)
                                            novos = [a for a in adicionais if a.lower() not in nomes_existentes]

                                            if novos:
                                                print(f"🆕 Novos adicionais detectados: {novos}")
                                                # Busca preços dos NOVOS adicionais do produto
                                                preco_novos = 0.0
                                                checkout_novos = []
                                                try:
                                                    complementos_prod = self.ingredientes_service.buscar_complementos_por_nome_receita(nome_produto)
                                                    if complementos_prod:
                                                        for comp in complementos_prod:
                                                            comp_id = comp.get('id')
                                                            adds_do_comp = []
                                                            for add in comp.get('adicionais', []):
                                                                add_nome = add.get('nome', '')
                                                                add_id = add.get('id')
                                                                for novo in novos:
                                                                    if add_nome.lower() == novo.lower() or novo.lower() in add_nome.lower() or add_nome.lower() in novo.lower():
                                                                        preco_novos += add.get('preco', 0)
                                                                        adds_do_comp.append({'adicional_id': add_id, 'quantidade': 1})
                                                                        break
                                                            if adds_do_comp:
                                                                checkout_novos.append({'complemento_id': comp_id, 'adicionais': adds_do_comp})
                                                except Exception as e:
                                                    print(f"Erro ao buscar complementos: {e}")

                                                # Mescla novos com existentes
                                                item_existente["adicionais"] = adicionais_existentes + novos
                                                item_existente["preco_adicionais"] = preco_existente + preco_novos
                                                item_existente["complementos_checkout"] = checkout_existente + checkout_novos
                                                print(f"💰 Preço adicionais: R$ {item_existente['preco_adicionais']:.2f} (existente: {preco_existente}, novos: {preco_novos})")
                                            else:
                                                # LLM apenas ecoou os mesmos - mantém existentes
                                                print(f"💰 Mantendo preco_adicionais existente: R$ {preco_existente:.2f}")
                                        else:
                                            # Sem adicionais novos - mantém existentes
                                            if adicionais_existentes:
                                                print(f"💰 Preservando adicionais existentes: {adicionais_existentes}, R$ {preco_existente:.2f}")
                                        # NÃO atualiza ultimo_produto_adicionado para item existente
                                        # Atualiza quantidade se for diferente
                                        nova_qtd = item.get("quantidade", 1)
                                        if nova_qtd != item_existente.get("quantidade", 1):
                                            item_existente["quantidade"] = nova_qtd
                                        print(f"✏️ Item atualizado no contexto: {item_existente}")
                                        mostrar_resumo = True
                                    else:
                                        # Adiciona novo item
                                        novo_item = {
                                            "id": produto_encontrado.get("id", ""),
                                            "nome": nome_produto,
                                            "descricao": produto_encontrado.get("descricao", ""),
                                            "quantidade": item.get("quantidade", 1),
                                            "preco": produto_encontrado["preco"],
                                            "removidos": removidos,
                                            "adicionais": adicionais
                                        }

                                        # Se tem adicionais, calcula preço e busca IDs
                                        if adicionais:
                                            preco_adicionais = 0.0
                                            complementos_checkout = []
                                            # Busca complementos do produto
                                            try:
                                                complementos_prod = self.ingredientes_service.buscar_complementos_por_nome_receita(nome_produto)
                                                if complementos_prod:
                                                    for comp in complementos_prod:
                                                        comp_id = comp.get('id')
                                                        adicionais_do_comp = []
                                                        for add in comp.get('adicionais', []):
                                                            add_nome = add.get('nome', '')
                                                            add_id = add.get('id')
                                                            for sel in adicionais:
                                                                if add_nome.lower() == sel.lower() or sel.lower() in add_nome.lower() or add_nome.lower() in sel.lower():
                                                                    preco_adicionais += add.get('preco', 0)
                                                                    adicionais_do_comp.append({
                                                                        'adicional_id': add_id,
                                                                        'quantidade': 1
                                                                    })
                                                                    break
                                                        if adicionais_do_comp:
                                                            complementos_checkout.append({
                                                                'complemento_id': comp_id,
                                                                'adicionais': adicionais_do_comp
                                                            })
                                            except Exception as e:
                                                print(f"Erro ao buscar complementos: {e}")

                                            novo_item['preco_adicionais'] = preco_adicionais
                                            novo_item['complementos_checkout'] = complementos_checkout
                                            print(f"💰 Preço adicionais calculado: R$ {preco_adicionais:.2f}")

                                        pedido_contexto.append(novo_item)
                                        print(f"🛒 Item adicionado ao contexto: {novo_item}")
                                        # Salva o último produto adicionado APENAS para novos itens
                                        dados['ultimo_produto_adicionado'] = produto_encontrado
                                        mostrar_resumo = True

                        elif acao == "remover" and itens:
                            # Remove itens do contexto
                            for item in itens:
                                nome_remover = item.get("nome", "").lower()
                                pedido_contexto = [p for p in pedido_contexto if nome_remover not in p["nome"].lower()]
                                print(f"🗑️ Item removido do contexto: {nome_remover}")

                        elif acao == "personalizar" and itens:
                            # Personaliza itens (geralmente o último pedido)
                            if pedido_contexto:
                                for item in itens:
                                    # Busca o item no pedido pelo nome, ou pega o último
                                    nome_item = item.get("nome", "").lower()
                                    item_para_personalizar = None
                                    for p in reversed(pedido_contexto):
                                        if nome_item in p["nome"].lower():
                                            item_para_personalizar = p
                                            break
                                    if not item_para_personalizar:
                                        item_para_personalizar = pedido_contexto[-1]

                                    if item.get("removidos"):
                                        item_para_personalizar["removidos"] = item["removidos"]
                                    if item.get("adicionais"):
                                        item_para_personalizar["adicionais"] = item["adicionais"]
                                    print(f"✏️ Item personalizado: {item_para_personalizar}")

                        elif acao == "selecionar_complementos":
                            # Cliente selecionou complementos - ADICIONA aos existentes do último item
                            complementos_selecionados = resposta_json.get("complementos_selecionados", [])
                            if complementos_selecionados and pedido_contexto:
                                ultimo_item = pedido_contexto[-1]

                                # PRESERVA adicionais existentes e seus preços
                                adicionais_existentes = ultimo_item.get('adicionais', [])
                                preco_existente = ultimo_item.get('preco_adicionais', 0.0)
                                checkout_existente = ultimo_item.get('complementos_checkout', [])

                                # Novos adicionais a serem adicionados
                                novos_nomes = []
                                novo_preco = 0.0
                                novos_checkout = []
                                tinha_obrigatorio = ultimo_item.get('complemento_obrigatorio', False)
                                tem_obrigatorio = tinha_obrigatorio  # Preserva se já tinha

                                # Função auxiliar para extrair quantidade do formato "Nx Nome"
                                def extrair_quantidade_nome(sel: str) -> tuple:
                                    """Extrai quantidade e nome de strings como '2x Maionese' ou 'Maionese'"""
                                    import re
                                    # Padrão: "2x Nome" ou "2 x Nome"
                                    match = re.match(r'^(\d+)\s*x\s*(.+)$', sel.strip(), re.IGNORECASE)
                                    if match:
                                        return int(match.group(1)), match.group(2).strip()
                                    return 1, sel.strip()

                                # Busca IDs e preços dos complementos selecionados
                                for comp in complementos_disponiveis:
                                    comp_id = comp.get('id')
                                    comp_obrigatorio = comp.get('obrigatorio', False)
                                    adicionais_do_comp = []

                                    for add in comp.get('adicionais', []):
                                        add_nome = add.get('nome', '')
                                        add_id = add.get('id')
                                        add_preco = add.get('preco', 0)

                                        for sel in complementos_selecionados:
                                            # Extrai quantidade do formato "Nx Nome"
                                            qtd_sel, nome_sel = extrair_quantidade_nome(sel)

                                            # Match por nome exato ou parcial
                                            if add_nome.lower() == nome_sel.lower() or nome_sel.lower() in add_nome.lower():
                                                # Verifica se já existe este adicional
                                                nome_base = add_nome  # Nome sem quantidade para checagem
                                                ja_existe = any(nome_base in existing for existing in adicionais_existentes)
                                                ja_novo = any(nome_base in novo for novo in novos_nomes)

                                                if not ja_existe and not ja_novo:
                                                    # Adiciona com quantidade no nome para exibição
                                                    nome_exibicao = f"{qtd_sel}x {add_nome}" if qtd_sel > 1 else add_nome
                                                    novos_nomes.append(nome_exibicao)
                                                    novo_preco += add_preco * qtd_sel  # Multiplica pelo quantidade
                                                    adicionais_do_comp.append({
                                                        'adicional_id': add_id,
                                                        'quantidade': qtd_sel  # Usa a quantidade extraída
                                                    })
                                                    # Marca se veio de complemento obrigatório
                                                    if comp_obrigatorio:
                                                        tem_obrigatorio = True
                                                    print(f"📦 Adicional: {nome_exibicao} (qtd: {qtd_sel}, preço unitário: R$ {add_preco:.2f})")
                                                break

                                    if adicionais_do_comp:
                                        # Verifica se já existe checkout para este complemento
                                        checkout_comp_existente = None
                                        for c in checkout_existente:
                                            if c.get('complemento_id') == comp_id:
                                                checkout_comp_existente = c
                                                break

                                        if checkout_comp_existente:
                                            # Adiciona aos adicionais existentes deste complemento
                                            for add in adicionais_do_comp:
                                                if add not in checkout_comp_existente['adicionais']:
                                                    checkout_comp_existente['adicionais'].append(add)
                                        else:
                                            novos_checkout.append({
                                                'complemento_id': comp_id,
                                                'adicionais': adicionais_do_comp
                                            })

                                # VALIDAÇÃO: Verifica regras de obrigatório, mínimo e máximo
                                erros_validacao = []
                                for comp in complementos_disponiveis:
                                    comp_id = comp.get('id')
                                    comp_nome = comp.get('nome', '')
                                    comp_obrigatorio = comp.get('obrigatorio', False)
                                    comp_minimo = comp.get('minimo_itens', 0)
                                    comp_maximo = comp.get('maximo_itens', 0)
                                    
                                    # Conta quantos itens deste complemento foram selecionados (existentes + novos)
                                    # Considera a quantidade de cada adicional (não apenas a contagem)
                                    qtd_selecionada = 0
                                    for checkout_comp in checkout_existente + novos_checkout:
                                        if checkout_comp.get('complemento_id') == comp_id:
                                            for add in checkout_comp.get('adicionais', []):
                                                # Soma a quantidade de cada adicional
                                                qtd_selecionada += add.get('quantidade', 1)
                                    
                                    # Valida obrigatório
                                    if comp_obrigatorio and qtd_selecionada == 0:
                                        erros_validacao.append(f"⚠️ *{comp_nome}* é obrigatório! Escolha pelo menos {comp_minimo} opção(ões).")
                                    
                                    # Valida mínimo
                                    if comp_minimo > 0 and qtd_selecionada < comp_minimo:
                                        erros_validacao.append(f"⚠️ *{comp_nome}*: escolha pelo menos {comp_minimo} opção(ões). Você escolheu {qtd_selecionada}.")
                                    
                                    # Valida máximo
                                    if comp_maximo > 0 and qtd_selecionada > comp_maximo:
                                        erros_validacao.append(f"⚠️ *{comp_nome}*: máximo {comp_maximo} opção(ões). Você escolheu {qtd_selecionada}.")
                                
                                # Se houver erros de validação, não finaliza e mostra os erros
                                if erros_validacao:
                                    mensagem_erro = "\n".join(erros_validacao)
                                    mensagem_erro += f"\n\n{self.ingredientes_service.formatar_complementos_para_chat(complementos_disponiveis, ultimo_item.get('nome', ''))}"
                                    mensagem_erro += "\n\nEscolha novamente seguindo as regras acima! 😊"
                                    dados['aguardando_complemento'] = True  # Mantém aguardando
                                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                                    return mensagem_erro
                                
                                # Mescla com existentes
                                todos_adicionais = adicionais_existentes + novos_nomes
                                total_preco = preco_existente + novo_preco
                                todos_checkout = checkout_existente + novos_checkout

                                ultimo_item['adicionais'] = todos_adicionais
                                ultimo_item['complementos_checkout'] = todos_checkout
                                ultimo_item['preco_adicionais'] = total_preco
                                ultimo_item['complemento_obrigatorio'] = tem_obrigatorio
                                dados['aguardando_complemento'] = False
                                dados['complementos_disponiveis'] = []
                                # IMPORTANTE: Limpa ultimo_produto_adicionado para não mostrar complementos novamente
                                dados['ultimo_produto_adicionado'] = None
                                print(f"✅ Complementos adicionados: {novos_nomes}, total agora: {todos_adicionais}")
                                print(f"💰 Preço adicionais: R$ {total_preco:.2f} (novo: R$ {novo_preco:.2f})")
                                print(f"📦 Estrutura para checkout: {todos_checkout}")
                                mostrar_resumo = True

                        elif acao == "pular_complementos":
                            # Cliente não quer complementos - VALIDA se há obrigatórios
                            if pedido_contexto:
                                # Verifica se há complementos obrigatórios não selecionados
                                tem_obrigatorio_nao_selecionado = False
                                mensagem_obrigatorio = ""
                                
                                for comp in complementos_disponiveis:
                                    if comp.get('obrigatorio', False):
                                        comp_id = comp.get('id')
                                        comp_nome = comp.get('nome', '')
                                        comp_minimo = comp.get('minimo_itens', 1)
                                        
                                        # Verifica se foi selecionado (considera quantidade total)
                                        foi_selecionado = False
                                        if pedido_contexto:
                                            ultimo_item = pedido_contexto[-1]
                                            checkout_existente = ultimo_item.get('complementos_checkout', [])
                                            qtd_total = 0
                                            for checkout_comp in checkout_existente:
                                                if checkout_comp.get('complemento_id') == comp_id:
                                                    # Soma as quantidades de todos os adicionais deste complemento
                                                    for add in checkout_comp.get('adicionais', []):
                                                        qtd_total += add.get('quantidade', 1)
                                                    if qtd_total >= comp_minimo:
                                                        foi_selecionado = True
                                                        break
                                        
                                        if not foi_selecionado:
                                            tem_obrigatorio_nao_selecionado = True
                                            mensagem_obrigatorio += f"\n⚠️ *{comp_nome}* é obrigatório! Escolha pelo menos {comp_minimo} opção(ões)."
                                
                                if tem_obrigatorio_nao_selecionado:
                                    mensagem_erro = "Não posso pular! Você precisa escolher os complementos obrigatórios:" + mensagem_obrigatorio
                                    mensagem_erro += f"\n\n{self.ingredientes_service.formatar_complementos_para_chat(complementos_disponiveis, pedido_contexto[-1].get('nome', ''))}"
                                    dados['aguardando_complemento'] = True  # Mantém aguardando
                                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                                    return mensagem_erro
                                
                                # Se não há obrigatórios ou todos foram selecionados, pode pular
                                dados['aguardando_complemento'] = False
                                dados['complementos_disponiveis'] = []
                                # IMPORTANTE: Limpa ultimo_produto_adicionado para não mostrar complementos novamente
                                dados['ultimo_produto_adicionado'] = None
                                print(f"⏭️ Cliente pulou complementos (opcionais ou já selecionados)")
                                mostrar_resumo = True

                        elif acao == "nenhuma" and itens and pedido_contexto:
                            # LLM retornou "nenhuma" mas pode ter adicionais mencionados
                            # Isso acontece quando o usuário adiciona mais complementos depois
                            for item in itens:
                                nome_item = item.get("nome", "").lower()
                                adicionais_llm = item.get("adicionais", [])

                                if adicionais_llm:
                                    # Encontra o item correspondente no contexto
                                    item_contexto = None
                                    for p in pedido_contexto:
                                        if p["nome"].lower() == nome_item:
                                            item_contexto = p
                                            break

                                    if item_contexto:
                                        adicionais_existentes = item_contexto.get('adicionais', [])
                                        # Verifica se há novos adicionais
                                        novos = [a for a in adicionais_llm if a not in adicionais_existentes]

                                        if novos:
                                            print(f"🔍 [Ação nenhuma] Detectados novos adicionais: {novos}")
                                            # Busca preços e IDs dos novos adicionais
                                            try:
                                                complementos_prod = self.ingredientes_service.buscar_complementos_por_nome_receita(item_contexto['nome'])
                                                if complementos_prod:
                                                    preco_novo = 0.0
                                                    checkout_novo = []

                                                    for comp in complementos_prod:
                                                        comp_id = comp.get('id')
                                                        adds_do_comp = []

                                                        for add in comp.get('adicionais', []):
                                                            add_nome = add.get('nome', '')
                                                            add_id = add.get('id')

                                                            for novo_add in novos:
                                                                if add_nome.lower() == novo_add.lower() or novo_add.lower() in add_nome.lower() or add_nome.lower() in novo_add.lower():
                                                                    preco_novo += add.get('preco', 0)
                                                                    adds_do_comp.append({
                                                                        'adicional_id': add_id,
                                                                        'quantidade': 1
                                                                    })
                                                                    break

                                                        if adds_do_comp:
                                                            checkout_novo.append({
                                                                'complemento_id': comp_id,
                                                                'adicionais': adds_do_comp
                                                            })

                                                    # Mescla com existentes
                                                    item_contexto['adicionais'] = adicionais_existentes + novos
                                                    item_contexto['preco_adicionais'] = item_contexto.get('preco_adicionais', 0) + preco_novo
                                                    item_contexto['complementos_checkout'] = item_contexto.get('complementos_checkout', []) + checkout_novo
                                                    print(f"✅ [Ação nenhuma] Adicionais atualizados: {item_contexto['adicionais']}, preco: R$ {item_contexto['preco_adicionais']:.2f}")
                                                    mostrar_resumo = True
                                            except Exception as e:
                                                print(f"Erro ao processar adicionais em ação nenhuma: {e}")

                        elif acao == "prosseguir_entrega":
                            # VERIFICA SE ACEITA PEDIDOS ANTES DE FINALIZAR
                            config = self._get_chatbot_config()
                            if config and not config.aceita_pedidos_whatsapp:
                                # Busca link do cardápio da empresa
                                try:
                                    empresa_query = text("""
                                        SELECT nome, cardapio_link
                                        FROM cadastros.empresas
                                        WHERE id = :empresa_id
                                    """)
                                    result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                                    empresa = result.fetchone()
                                    link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                                except Exception as e:
                                    print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                                    link_cardapio = LINK_CARDAPIO
                                
                                # Retorna mensagem de redirecionamento
                                if config.mensagem_redirecionamento:
                                    resposta_redir = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                                else:
                                    resposta_redir = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                                
                                # Salva no histórico e retorna
                                historico.append({"role": "assistant", "content": resposta_redir})
                                dados['historico'] = historico
                                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                                return resposta_redir
                            
                            # Cliente quer finalizar - converter contexto em carrinho
                            if pedido_contexto:
                                print(f"🚗 Prosseguindo para entrega com {len(pedido_contexto)} itens")
                                dados['carrinho'] = self._converter_contexto_para_carrinho(pedido_contexto)
                                dados['pedido_contexto'] = pedido_contexto
                                self._salvar_estado_conversa(user_id, STATE_PERGUNTANDO_ENTREGA_RETIRADA, dados)
                                # Retorna mensagem padrão do fluxo de entrega
                                return self._perguntar_entrega_ou_retirada(user_id, dados)
                            else:
                                return "Você ainda não pediu nada! O que vai querer? 😊"

                        # Salva estado atualizado
                        dados['pedido_contexto'] = pedido_contexto
                        dados['historico'] = historico
                        dados['historico'].append({"role": "assistant", "content": resposta_texto})
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)

                        # Remove qualquer JSON residual da resposta
                        resposta_limpa = resposta_texto
                        # Se a resposta começa com { é JSON bruto, usa só o campo "resposta"
                        if resposta_limpa.strip().startswith('{'):
                            resposta_limpa = re.sub(r'\{[\s\S]*\}', '', resposta_limpa).strip()
                        # Remove qualquer JSON no meio do texto
                        resposta_limpa = re.sub(r'\{[^}]*"resposta"[^}]*\}', '', resposta_limpa).strip()
                        resposta_limpa = re.sub(r'\{[^}]*"acao"[^}]*\}', '', resposta_limpa).strip()
                        # Se ficou vazio, usa a resposta extraída do JSON
                        if not resposta_limpa:
                            resposta_limpa = resposta_json.get("resposta", "Anotado! Quer mais algo? 😊")

                        # Se adicionou item, mostra resumo do pedido
                        if mostrar_resumo and pedido_contexto:
                            # Calcula total incluindo preço dos adicionais
                            total = 0
                            for item in pedido_contexto:
                                preco_base = item.get('preco', 0)
                                preco_adicionais = item.get('preco_adicionais', 0)
                                qtd = item.get('quantidade', 1)
                                total += (preco_base + preco_adicionais) * qtd

                            resumo = f"\n\n📋 *Seu pedido até agora:*\n"
                            for item in pedido_contexto:
                                qtd = item.get('quantidade', 1)
                                nome = item.get('nome', '')
                                preco_unit = item.get('preco', 0)
                                preco_adicionais = item.get('preco_adicionais', 0)
                                preco_total = (preco_unit + preco_adicionais) * qtd
                                descricao = item.get('descricao', '')
                                resumo += f"• {qtd}x {nome} - R$ {preco_total:.2f}\n"
                                if descricao:
                                    resumo += f"  _{descricao}_\n"
                                if item.get('removidos'):
                                    resumo += f"  _Sem: {', '.join(item['removidos'])}_\n"
                                for add in item.get('adicionais', []):
                                    nome = add.get('nome', add) if isinstance(add, dict) else add
                                    preco = add.get('preco', 0) if isinstance(add, dict) else 0
                                    resumo += f"        ➕ {nome}" + (f" (+R$ {preco:.2f})" if preco > 0 else "") + "\n"

                            taxa_entrega = dados.get('taxa_entrega', 0.0)
                            if taxa_entrega and taxa_entrega > 0:
                                resumo += f"\ntaxa de entrega: {taxa_entrega:.2f}"
                            resumo += f"\n💰 *Total: R$ {(total + (taxa_entrega or 0.0)):.2f}*"
                            resposta_limpa += resumo

                            # Verifica se acabou de adicionar complementos (não mostrar de novo)
                            aguardando = dados.get('aguardando_complemento', False)
                            ultimo_item = pedido_contexto[-1] if pedido_contexto else None
                            adicionais_selecionados = ultimo_item.get('adicionais', []) if ultimo_item else []

                            # Se estava aguardando e já tem adicionais, limpa o estado
                            if aguardando and adicionais_selecionados:
                                dados['aguardando_complemento'] = False
                                resposta_limpa += "\n\nQuer mais alguma coisa? 😊"
                            else:
                                # Verifica se o último produto adicionado tem complementos
                                ultimo_produto = dados.get('ultimo_produto_adicionado')
                                if ultimo_produto and not adicionais_selecionados:
                                    nome_produto = ultimo_produto.get('nome', '')
                                    try:
                                        complementos = self.ingredientes_service.buscar_complementos_por_nome_receita(nome_produto)
                                        if complementos:
                                            tem_obrigatorio = self.ingredientes_service.tem_complementos_obrigatorios(complementos)
                                            if tem_obrigatorio:
                                                # Remove "Quer mais algo?" pois vamos perguntar sobre complementos
                                                resposta_limpa = resposta_limpa.replace("Quer mais algo?", "").replace("Quer mais algo? 😊", "").strip()
                                                # Mostra complementos obrigatórios com mensagem amigável
                                                resposta_limpa += self.ingredientes_service.formatar_complementos_para_chat(complementos, nome_produto)
                                                # Mensagem mais amigável baseada no min/max
                                                for comp in complementos:
                                                    if comp.get('obrigatorio'):
                                                        minimo = comp.get('minimo_itens', 1)
                                                        resposta_limpa += f"\n\n👆 Escolha pelo menos {minimo} opção(ões) de *{comp.get('nome', 'complemento').upper()}* para o seu {nome_produto}!"
                                                        break
                                                dados['complementos_disponiveis'] = complementos
                                                dados['aguardando_complemento'] = True
                                                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                                            else:
                                                # Opcionais - pergunta de forma compacta e rápida
                                                resposta_limpa = resposta_limpa.replace("Quer mais algo?", "").replace("Quer mais algo? 😊", "").strip()
                                                # Cria lista resumida de complementos disponíveis
                                                nomes_complementos = [comp.get('nome', 'Complemento') for comp in complementos]
                                                if len(nomes_complementos) == 1:
                                                    resposta_limpa += f"\n\n💬 Quer adicionar *{nomes_complementos[0]}*? (Digite o que deseja ou 'não' para continuar)"
                                                elif len(nomes_complementos) <= 3:
                                                    complementos_txt = ", ".join([f"*{nome}*" for nome in nomes_complementos[:-1]])
                                                    resposta_limpa += f"\n\n💬 Quer adicionar algum complemento? Temos {complementos_txt} ou *{nomes_complementos[-1]}*.\n(Digite o que deseja ou 'não' para continuar)"
                                                else:
                                                    resposta_limpa += f"\n\n💬 Quer adicionar algum complemento? Temos {len(complementos)} opções disponíveis.\n(Digite o que deseja ou 'não' para continuar)"
                                                dados['complementos_disponiveis'] = complementos
                                                dados['aguardando_complemento'] = True
                                                dados['ultimo_produto_com_complementos'] = nome_produto
                                    except Exception as e:
                                        print(f"Erro ao buscar complementos: {e}")

                        return resposta_limpa

                    except json.JSONDecodeError:
                        # Se não conseguiu parsear JSON, tenta extrair texto limpo
                        # Remove qualquer coisa que pareça JSON
                        resposta_limpa = re.sub(r'\{[\s\S]*\}', '', resposta_ia).strip()
                        if not resposta_limpa:
                            resposta_limpa = resposta_ia

                        dados['historico'] = historico
                        dados['historico'].append({"role": "assistant", "content": resposta_limpa})
                        self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                        return resposta_limpa

                else:
                    print(f"❌ Erro Groq: {response.status_code}")
                    # Fallback inteligente em vez de erro
                    return await self._fallback_resposta_inteligente(mensagem, dados, user_id)

        except Exception as e:
            print(f"❌ Erro na conversa IA: {e}")
            # Verifica se o erro é por falta de GROQ_API_KEY
            is_api_key_missing = "GROQ_API_KEY não configurada" in str(e) or not GROQ_API_KEY or not GROQ_API_KEY.strip()
            
            if is_api_key_missing:
                # Se a IA não está disponível, usa fallback mas não desativa o chatbot
                return await self._fallback_resposta_inteligente(mensagem, dados, user_id, skip_desativar=True)
            else:
                # Fallback inteligente - analisa a mensagem e responde de forma natural
                return await self._fallback_resposta_inteligente(mensagem, dados, user_id)

    async def _fallback_resposta_inteligente(self, mensagem: str, dados: dict, user_id: str = None, skip_desativar: bool = False) -> str:
        """
        Fallback quando a IA falha - analisa a mensagem e toma uma decisão inteligente.
        Nunca retorna erro genérico.
        
        Args:
            skip_desativar: Se True, não desativa o chatbot mesmo quando não entende a mensagem
                           (útil quando a IA não está disponível por falta de API key)
        """
        msg_lower = mensagem.lower().strip()
        pedido_contexto = dados.get('pedido_contexto', [])
        todos_produtos = self._buscar_todos_produtos()
        if not user_id:
            user_id = dados.get('user_id', '')

        # 0. PRIMEIRO: Verifica se está aguardando seleção de complementos
        aguardando_complemento = dados.get('aguardando_complemento', False)
        complementos_disponiveis = dados.get('complementos_disponiveis', [])

        if aguardando_complemento and complementos_disponiveis and pedido_contexto:
            # Tenta encontrar complementos mencionados na mensagem
            nomes_adicionais = []
            preco_total_complementos = 0.0
            complementos_checkout = []  # Para enviar ao endpoint

            def normalizar(texto):
                acentos = {'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
                           'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u', 'ç': 'c'}
                texto = texto.lower()
                for ac, sem in acentos.items():
                    texto = texto.replace(ac, sem)
                return texto

            def extrair_quantidade_mensagem(msg: str, nome_adicional: str) -> int:
                """Extrai quantidade da mensagem para um adicional específico"""
                import re
                msg_norm = normalizar(msg)
                nome_norm = normalizar(nome_adicional)
                primeira_palavra = nome_norm.split()[0] if nome_norm else ''

                # Padrões: "2 maionese", "2x maionese", "quero 2 maionese"
                padroes = [
                    rf'(\d+)\s*x?\s*{re.escape(primeira_palavra)}',  # "2 maionese" ou "2x maionese"
                    rf'quero\s+(\d+)\s+{re.escape(primeira_palavra)}',  # "quero 2 maionese"
                ]
                for padrao in padroes:
                    match = re.search(padrao, msg_norm)
                    if match:
                        return int(match.group(1))
                return 1  # Default: 1 unidade

            msg_norm = normalizar(msg_lower)

            for comp in complementos_disponiveis:
                comp_id = comp.get('id')
                adicionais_do_comp = []

                for adicional in comp.get('adicionais', []):
                    add_nome = adicional.get('nome', '')
                    add_id = adicional.get('id')
                    add_preco = adicional.get('preco', 0)
                    add_nome_norm = normalizar(add_nome)
                    primeira_palavra = add_nome_norm.split()[0] if add_nome_norm else ''

                    encontrado = False
                    if add_nome_norm in msg_norm:
                        encontrado = True
                    elif len(primeira_palavra) > 3:
                        palavras_genericas = ['extra', 'ml', 'com', 'sem', 'gratis']
                        if primeira_palavra not in palavras_genericas and primeira_palavra in msg_norm:
                            encontrado = True

                    if encontrado and add_nome not in [n.split('x ')[-1] if 'x ' in n else n for n in nomes_adicionais]:
                        # Extrai quantidade da mensagem
                        qtd = extrair_quantidade_mensagem(msg_lower, add_nome)
                        nome_exibicao = f"{qtd}x {add_nome}" if qtd > 1 else add_nome
                        nomes_adicionais.append(nome_exibicao)
                        preco_total_complementos += add_preco * qtd  # Multiplica pela quantidade
                        adicionais_do_comp.append({
                            'adicional_id': add_id,
                            'quantidade': qtd  # Usa quantidade extraída
                        })
                        print(f"📦 [Fallback] Adicional: {nome_exibicao} (qtd: {qtd}, preço unitário: R$ {add_preco:.2f})")

                if adicionais_do_comp:
                    complementos_checkout.append({
                        'complemento_id': comp_id,
                        'adicionais': adicionais_do_comp
                    })

            if nomes_adicionais:
                ultimo_item = pedido_contexto[-1]

                # PRESERVA adicionais existentes e mescla com novos
                adicionais_existentes = ultimo_item.get('adicionais', [])
                preco_existente = ultimo_item.get('preco_adicionais', 0.0)
                checkout_existente = ultimo_item.get('complementos_checkout', [])

                # Filtra apenas novos (que não existem ainda)
                novos_nomes = [n for n in nomes_adicionais if n not in adicionais_existentes]

                # Mescla com existentes
                todos_adicionais = adicionais_existentes + novos_nomes
                total_preco = preco_existente + preco_total_complementos
                todos_checkout = checkout_existente + complementos_checkout

                ultimo_item['adicionais'] = todos_adicionais
                ultimo_item['complementos_checkout'] = todos_checkout
                ultimo_item['preco_adicionais'] = total_preco
                dados['pedido_contexto'] = pedido_contexto
                dados['aguardando_complemento'] = False
                dados['complementos_disponiveis'] = []
                # IMPORTANTE: Limpa ultimo_produto_adicionado para não mostrar complementos novamente
                dados['ultimo_produto_adicionado'] = None
                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                print(f"✅ [Fallback] Novos complementos: {novos_nomes}, total agora: {todos_adicionais}")

                total = sum((item.get('preco', 0) + item.get('preco_adicionais', 0)) * item.get('quantidade', 1) for item in pedido_contexto)
                resp = f"✅ Adicionei *{', '.join(nomes_adicionais)}*!\n\n"
                resp += "📋 *Seu pedido até agora:*\n"
                for item in pedido_contexto:
                    qtd = item.get('quantidade', 1)
                    preco = (item.get('preco', 0) + item.get('preco_adicionais', 0)) * qtd
                    resp += f"• {qtd}x {item['nome']} - R$ {preco:.2f}\n"
                    if item.get('descricao'):
                        resp += f"  _{item['descricao']}_\n"
                    if item.get('removidos'):
                        resp += f"  _Sem: {', '.join(item['removidos'])}_\n"
                    if item.get('adicionais'):
                        for add in item['adicionais']:
                            nome = add.get('nome', add) if isinstance(add, dict) else add
                            preco = add.get('preco', 0) if isinstance(add, dict) else 0
                            if preco and preco > 0:
                                resp += f"        ➕ {nome} (+R$ {preco:.2f})\n"
                            else:
                                resp += f"        ➕ {nome}\n"

                taxa_entrega = dados.get('taxa_entrega', 0.0)
                if taxa_entrega and taxa_entrega > 0:
                    resp += f"\ntaxa de entrega: {taxa_entrega:.2f}"
                resp += f"\n💰 *Total: R$ {(total + (taxa_entrega or 0.0)):.2f}*"
                resp += "\n\nQuer mais alguma coisa? 😊"
                return resp

        # 1. Saudações - pode retornar boas-vindas (dependendo do modo)
        saudacoes = ['oi', 'olá', 'ola', 'hey', 'eae', 'e ai', 'opa', 'bom dia', 'boa tarde', 'boa noite', 'tudo bem', 'tudo bom']
        if self.emit_welcome_message and any(s in msg_lower for s in saudacoes):
            return self._gerar_mensagem_boas_vindas_conversacional()

        # 2. PERGUNTAS SOBRE PRODUTOS - Detecta perguntas sobre ingredientes/composição
        # Exemplos: "O que vem nele", "O que tem no xburger", "Quais ingredientes do xburger"
        quer_saber, nome_produto = detectar_pergunta_ingredientes(mensagem)
        if quer_saber and nome_produto:
            print(f"🔍 [Fallback] Detectada pergunta sobre produto: '{nome_produto}'")
            # Busca o produto
            produto_encontrado = self._buscar_produto_por_termo(nome_produto, todos_produtos)
            if produto_encontrado:
                # Usa o método que busca ingredientes reais do banco
                return self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
            else:
                # Produto não encontrado - tenta buscar por palavras-chave
                # Se a mensagem contém "nele", "nele", pode ser sobre o último produto adicionado
                if 'nele' in msg_lower or 'nele' in msg_lower or 'nele' in msg_lower:
                    if pedido_contexto:
                        ultimo_produto = pedido_contexto[-1]
                        produto_encontrado = self._buscar_produto_por_termo(ultimo_produto.get('nome', ''), todos_produtos)
                        if produto_encontrado:
                            return self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                return f"Hmm, não encontrei o produto '{nome_produto}' no cardápio. Quer ver o cardápio completo? 😊"
        
        # Também detecta padrões mais simples como "o que vem no X", "que tem no Y"
        padroes_pergunta = [
            r'o\s+que\s+(?:vem|tem)\s+(?:no|na|n[oa])\s+(.+?)(?:\?|$)',
            r'que\s+(?:vem|tem)\s+(?:no|na|n[oa])\s+(.+?)(?:\?|$)',
            r'o\s+que\s+(?:vem|tem)\s+nele(?:\?|$)',
            r'que\s+(?:vem|tem)\s+nele(?:\?|$)',
        ]
        for padrao in padroes_pergunta:
            match = re.search(padrao, msg_lower)
            if match:
                produto_busca = match.group(1).strip() if match.lastindex else None
                # Se não tem grupo, pode ser "nele" - verifica último produto
                if not produto_busca or produto_busca == 'nele' or produto_busca == 'nele':
                    if pedido_contexto:
                        ultimo_produto = pedido_contexto[-1]
                        produto_encontrado = self._buscar_produto_por_termo(ultimo_produto.get('nome', ''), todos_produtos)
                        if produto_encontrado:
                            return self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                elif produto_busca and len(produto_busca) > 2:
                    produto_encontrado = self._buscar_produto_por_termo(produto_busca, todos_produtos)
                    if produto_encontrado:
                        return self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                break

        # 3. Pedido de cardápio
        if any(p in msg_lower for p in ['cardapio', 'cardápio', 'menu', 'o que tem', 'que tem', 'produtos']):
            return self._gerar_lista_produtos(todos_produtos, pedido_contexto)

        # 3. Quer fazer pedido / pedir algo
        # Também aceita pedidos diretos como "1 x-egg", "2 pizzas" (começa com número)
        tem_quantidade = bool(re.match(r'^\d+\s*', msg_lower))
        quer_pedir = any(p in msg_lower for p in ['quero', 'me ve', 'me vê', 'me da', 'me dá', 'fazer pedido', 'pedir', 'um ', 'uma ', 'uns ', 'umas '])

        if tem_quantidade or quer_pedir:
            # Tenta encontrar um produto na mensagem
            for produto in todos_produtos:
                nome_normalizado = re.sub(r'[-\s_.]', '', produto['nome'].lower())
                msg_normalizado = re.sub(r'[-\s_.]', '', msg_lower)
                if nome_normalizado in msg_normalizado or any(p in msg_lower for p in produto['nome'].lower().split()):
                    # Encontrou produto - adiciona ao pedido
                    quantidade = 1
                    nums = re.findall(r'\d+', mensagem)
                    if nums:
                        quantidade = int(nums[0])

                    # Verifica se quer tirar algo (sem cebola, tira o molho, etc)
                    removidos = []
                    padroes_remover = [
                        r'sem\s+(\w+)',
                        r'tira[r]?\s+(?:o\s+|a\s+)?(\w+)',
                        r'retira[r]?\s+(?:o\s+|a\s+)?(\w+)',
                        r'nao\s+quero\s+(\w+)',
                        r'não\s+quero\s+(\w+)'
                    ]
                    for padrao in padroes_remover:
                        matches = re.findall(padrao, msg_lower)
                        for m in matches:
                            if m not in ['nada', 'mais', 'isso']:
                                removidos.append(m.capitalize())

                    novo_item = {
                        "id": produto.get('id', ''),
                        "nome": produto['nome'],
                        "descricao": produto.get('descricao', ''),
                        "preco": produto['preco'],
                        "quantidade": quantidade,
                        "removidos": removidos,
                        "adicionais": []
                    }
                    pedido_contexto.append(novo_item)
                    dados['pedido_contexto'] = pedido_contexto
                    dados['ultimo_produto_adicionado'] = produto
                    user_id = dados.get('user_id', '')

                    # Monta resumo com detalhes
                    total = sum((i.get('preco', 0) + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)
                    resp = f"Anotado! {quantidade}x {produto['nome']}."
                    if removidos:
                        resp += f" (sem {', '.join(removidos)})"

                    resp += f"\n\n📋 *Seu pedido até agora:*\n"
                    for item in pedido_contexto:
                        qtd = item.get('quantidade', 1)
                        preco_total = (item.get('preco', 0) + item.get('preco_adicionais', 0)) * qtd
                        resp += f"• {qtd}x {item['nome']} - R$ {preco_total:.2f}\n"
                        if item.get('descricao'):
                            resp += f"  _{item['descricao']}_\n"
                        if item.get('removidos'):
                            resp += f"  _Sem: {', '.join(item['removidos'])}_\n"
                        if item.get('adicionais'):
                            for add in item['adicionais']:
                                nome = add.get('nome', add) if isinstance(add, dict) else add
                                preco = add.get('preco', 0) if isinstance(add, dict) else 0
                                if preco and preco > 0:
                                    resp += f"        ➕ {nome} (+R$ {preco:.2f})\n"
                                else:
                                    resp += f"        ➕ {nome}\n"
                    taxa_entrega = dados.get('taxa_entrega', 0.0)
                    if taxa_entrega and taxa_entrega > 0:
                        resp += f"\ntaxa de entrega: {taxa_entrega:.2f}"
                    resp += f"\n💰 *Total: R$ {(total + (taxa_entrega or 0.0)):.2f}*"

                    # Verifica se tem complementos obrigatórios
                    try:
                        complementos = self.ingredientes_service.buscar_complementos_por_nome_receita(produto['nome'])
                        if complementos:
                            tem_obrigatorio = self.ingredientes_service.tem_complementos_obrigatorios(complementos)
                            if tem_obrigatorio:
                                resp += self.ingredientes_service.formatar_complementos_para_chat(complementos, produto['nome'])
                                for comp in complementos:
                                    if comp.get('obrigatorio'):
                                        minimo = comp.get('minimo_itens', 1)
                                        resp += f"\n\n👆 Escolha pelo menos {minimo} opção(ões) de *{comp.get('nome', 'complemento').upper()}* para o seu {produto['nome']}!"
                                        break
                                dados['complementos_disponiveis'] = complementos
                                dados['aguardando_complemento'] = True
                            else:
                                # Complementos opcionais - pergunta de forma compacta
                                nomes_complementos = [comp.get('nome', 'Complemento') for comp in complementos]
                                if len(nomes_complementos) == 1:
                                    resp += f"\n\n💬 Quer adicionar *{nomes_complementos[0]}*? (Digite o que deseja ou 'não' para continuar)"
                                elif len(nomes_complementos) <= 3:
                                    complementos_txt = ", ".join([f"*{nome}*" for nome in nomes_complementos[:-1]])
                                    resp += f"\n\n💬 Quer adicionar algum complemento? Temos {complementos_txt} ou *{nomes_complementos[-1]}*.\n(Digite o que deseja ou 'não' para continuar)"
                                else:
                                    resp += f"\n\n💬 Quer adicionar algum complemento? Temos {len(complementos)} opções disponíveis.\n(Digite o que deseja ou 'não' para continuar)"
                                dados['complementos_disponiveis'] = complementos
                                dados['aguardando_complemento'] = True
                        else:
                            resp += "\n\nQuer mais alguma coisa? 😊"
                    except Exception as e:
                        print(f"Erro ao buscar complementos no fallback: {e}")
                        resp += "\n\nQuer mais alguma coisa? 😊"

                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    return resp

            # Não encontrou produto específico - pergunta o que quer
            return "Claro! O que você gostaria de pedir? 😊"

        # 4. Remover ingredientes (sem, tira, etc)
        padroes_remover = [
            r'sem\s+(\w+)',
            r'tira[r]?\s+(?:o\s+|a\s+)?(\w+)',
            r'retira[r]?\s+(?:o\s+|a\s+)?(\w+)'
        ]
        for padrao in padroes_remover:
            matches = re.findall(padrao, msg_lower)
            if matches and pedido_contexto:
                # Encontra qual item modificar (último ou especificado)
                item_alvo = pedido_contexto[-1]  # Default: último item
                for item in pedido_contexto:
                    if item['nome'].lower() in msg_lower:
                        item_alvo = item
                        break

                removidos = item_alvo.get('removidos', [])
                for match in matches:
                    ingrediente = match.capitalize()
                    if ingrediente not in removidos and ingrediente not in ['Nada', 'Mais', 'Isso']:
                        removidos.append(ingrediente)
                item_alvo['removidos'] = removidos

                # Calcula total com preco_adicionais
                total = sum((i['preco'] + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)

                resp = f"✅ Anotado! {item_alvo['nome']} agora vai *sem {', '.join(removidos)}*.\n\n"
                resp += "📋 *Seu pedido:*\n"
                for item in pedido_contexto:
                    preco_item = (item['preco'] + item.get('preco_adicionais', 0)) * item.get('quantidade', 1)
                    resp += f"• {item.get('quantidade', 1)}x {item['nome']} - R$ {preco_item:.2f}\n"
                    if item.get('removidos'):
                        resp += f"  _Sem: {', '.join(item['removidos'])}_\n"
                    if item.get('adicionais'):
                        for add in item['adicionais']:
                            nome = add.get('nome', add) if isinstance(add, dict) else add
                            preco = add.get('preco', 0) if isinstance(add, dict) else 0
                            if preco and preco > 0:
                                resp += f"        ➕ {nome} (+R$ {preco:.2f})\n"
                            else:
                                resp += f"        ➕ {nome}\n"
                resp += f"\n💰 *Total: R$ {total:.2f}*\n\nQuer mais alguma coisa? 😊"

                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                return resp

        # 5. Finalizar pedido - segue fluxo estruturado
        if any(p in msg_lower for p in ['so isso', 'só isso', 'fechar', 'finalizar', 'nao quero mais', 'não quero mais', 'pronto', 'acabou']):
            if pedido_contexto:
                # Converte pedido_contexto para carrinho se necessário
                carrinho_fallback = dados.get('carrinho', [])
                if not carrinho_fallback:
                    dados['carrinho'] = self._converter_contexto_para_carrinho(pedido_contexto)
                    dados['pedido_contexto'] = pedido_contexto
                
                # Inicia fluxo estruturado de finalização
                print("🛒 [Fallback] Detectado finalizar_pedido, iniciando fluxo estruturado")
                self._salvar_estado_conversa(user_id, STATE_PERGUNTANDO_ENTREGA_RETIRADA, dados)
                return self._perguntar_entrega_ou_retirada(user_id, dados)
            return "Você ainda não pediu nada! O que vai querer? 😊"

        # 5. Ver pedido atual
        if any(p in msg_lower for p in ['meu pedido', 'o que pedi', 'quanto ta', 'quanto tá', 'quanto deu', 'carrinho']):
            if pedido_contexto:
                total = sum((i['preco'] + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)
                resumo = "📋 *Seu pedido:*\n"
                for item in pedido_contexto:
                    preco_item = (item['preco'] + item.get('preco_adicionais', 0)) * item.get('quantidade', 1)
                    resumo += f"• {item.get('quantidade', 1)}x {item['nome']} - R$ {preco_item:.2f}\n"
                    if item.get('removidos'):
                        resumo += f"  _Sem: {', '.join(item['removidos'])}_\n"
                    if item.get('adicionais'):
                        for add in item['adicionais']:
                            nome = add.get('nome', add) if isinstance(add, dict) else add
                            preco = add.get('preco', 0) if isinstance(add, dict) else 0
                            if preco and preco > 0:
                                resumo += f"        ➕ {nome} (+R$ {preco:.2f})\n"
                            else:
                                resumo += f"        ➕ {nome}\n"
                resumo += f"\n💰 *Total: R$ {total:.2f}*\n\nQuer mais alguma coisa?"
                return resumo
            return "Seu carrinho está vazio! O que vai querer? 😊"

        # 6. Perguntas sobre estabelecimento (localização/horário) - DEVE vir ANTES de perguntas genéricas
        msg_lower_fallback = mensagem.lower()
        padroes_localizacao = [
            r'onde\s+(voc[eê]s\s+)?(fic|est[aá]|ficam|est[aã]o)',
            r'onde\s+(fic|est[aá])',
            r'qual\s+(o\s+)?(endere[cç]o|localiza[cç][aã]o)',
            r'localiza[cç][aã]o',
            r'endere[cç]o'
        ]
        padroes_horario = [
            r'(qual|que)\s+(o\s+)?hor[aá]rio',
            r'que\s+horas\s+(voc[eê]s\s+)?(abr|funcion)',
            r'at[eé]\s+que\s+horas',
            r'hor[aá]rio\s+(de\s+)?(funcionamento|trabalho)',
            r'funcionam\s+(at[eé]|at)'
        ]
        
        eh_pergunta_localizacao = any(re.search(p, msg_lower_fallback, re.IGNORECASE) for p in padroes_localizacao)
        eh_pergunta_horario = any(re.search(p, msg_lower_fallback, re.IGNORECASE) for p in padroes_horario)
        
        if eh_pergunta_localizacao or eh_pergunta_horario:
            # Trata como informar_sobre_estabelecimento
            tipo_pergunta = "ambos"
            if eh_pergunta_localizacao and not eh_pergunta_horario:
                tipo_pergunta = "localizacao"
            elif eh_pergunta_horario and not eh_pergunta_localizacao:
                tipo_pergunta = "horario"
            
            empresas = self._buscar_empresas_ativas()
            if not empresas:
                return "❌ Não foi possível obter informações do estabelecimento no momento. 😔"
            
            # Busca empresa atual
            empresa_atual = None
            for emp in empresas:
                if emp['id'] == self.empresa_id:
                    empresa_atual = emp
                    break
            
            resposta = ""
            
            if tipo_pergunta in ["horario", "ambos"]:
                if empresa_atual:
                    horarios = self._formatar_horarios_funcionamento(empresa_atual.get('horarios_funcionamento'))
                    resposta += horarios + "\n\n"
                else:
                    resposta += "Horários de funcionamento não disponíveis.\n\n"
            
            if tipo_pergunta in ["localizacao", "ambos"]:
                localizacao = self._formatar_localizacao_empresas(empresas, self.empresa_id)
                resposta += localizacao
            
            return resposta.strip() if resposta.strip() else "Informações não disponíveis no momento. 😔"

        # 7. Perguntas genéricas - responde de forma útil
        if '?' in mensagem:
            return "Hmm, deixa eu te ajudar! Posso te mostrar nosso cardápio ou tirar dúvidas sobre algum produto específico. O que prefere? 😊"

        # 8. Fallback final - sempre útil, nunca erro
        if pedido_contexto:
            total = sum((i['preco'] + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)
            return f"Entendi! Você já tem R$ {total:.2f} no pedido. Quer adicionar mais alguma coisa ou posso fechar? 😊"

        # Se chegou aqui, não conseguiu entender
        # Se skip_desativar=True (IA não disponível), responde de forma genérica sem desativar
        if skip_desativar:
            return (
                "Desculpe, não consegui entender completamente sua mensagem. 😔\n\n"
                "Você pode:\n"
                "• Ver nosso cardápio\n"
                "• Fazer um pedido\n"
                "• Tirar dúvidas sobre produtos\n"
                "• Chamar atendente\n\n"
                "O que você gostaria? 😊"
            )
        
        # Caso contrário, chama função de não entendimento (desativa chatbot)
        return await self._nao_entendeu_mensagem(user_id, mensagem, dados)

    def _formatar_cardapio_para_ia(self, produtos: List[Dict]) -> str:
        """Formata cardápio completo para o prompt da IA"""
        # Agrupa por categoria
        categorias = {}
        for p in produtos:
            cat = p.get('categoria', 'Outros')
            if cat not in categorias:
                categorias[cat] = []

            # Busca ingredientes
            ingredientes = self.ingredientes_service.buscar_ingredientes_por_nome_receita(p['nome'])
            ing_texto = ""
            if ingredientes:
                ing_texto = f" (Ingredientes: {', '.join([i['nome'] for i in ingredientes])})"

            categorias[cat].append(f"• {p['nome']} - R$ {p['preco']:.2f}{ing_texto}")

        # Busca adicionais
        adicionais = self.ingredientes_service.buscar_todos_adicionais()

        texto = ""
        for cat, items in categorias.items():
            texto += f"\n{cat}:\n"
            texto += "\n".join(items) + "\n"

        if adicionais:
            texto += "\n➕ ADICIONAIS DISPONÍVEIS:\n"
            for add in adicionais:
                texto += f"• {add['nome']} - +R$ {add['preco']:.2f}\n"

        return texto

    def _converter_contexto_para_carrinho(self, pedido_contexto: List[Dict]) -> List[Dict]:
        """Converte o contexto da conversa para formato de carrinho"""
        return self.carrinho_domain.converter_contexto_para_carrinho(pedido_contexto)

    def _eh_primeira_mensagem(self, mensagem: str) -> bool:
        """Detecta se é uma mensagem inicial/saudação"""
        msg_lower = mensagem.lower().strip()
        saudacoes = [
            'oi', 'ola', 'olá', 'hey', 'eai', 'e ai', 'opa', 'oie',
            'bom dia', 'boa tarde', 'boa noite', 'hello', 'hi',
            'início', 'inicio', 'começar'
        ]
        # Nota: 'cardapio', 'menu' removidos para permitir ver cardápio sem resetar conversa
        return any(msg_lower == s or msg_lower.startswith(s + ' ') for s in saudacoes)

    def _detectar_confirmacao_pedido(self, mensagem: str) -> bool:
        """Detecta se cliente quer finalizar/confirmar o pedido"""
        msg_lower = mensagem.lower().strip()

        # PRIMEIRO verifica confirmações explícitas de fechamento
        # (antes de verificar false_positives para evitar conflitos com "nao quero mais")
        confirmacoes_fechamento = [
            'fechar', 'finalizar', 'fechou', 'pronto', 'só isso',
            'so isso', 'é isso', 'e isso', 'confirmar pedido',
            'pode fechar', 'pode finalizar', 'tá bom', 'ta bom',
            'só isso mesmo', 'so isso mesmo', 'era isso', 'é só',
            'nao quero mais nada', 'não quero mais nada', 'mais nada',
            'nao quero mais', 'não quero mais', 'nao preciso mais', 'não preciso mais',
            'só', 'so', 'é so', 'e so', 'basta', 'chega', 'era so', 'era só',
            'acabou', 'terminei', 'completei'
        ]
        if any(c in msg_lower for c in confirmacoes_fechamento):
            return True

        # Palavras que NÃO são confirmação (evita falsos positivos)
        # IMPORTANTE: Só verifica DEPOIS das confirmações explícitas!
        false_positives = ['me ve', 'me vê', 'quero um', 'quero uma', 'manda', 'traz', 'quais', 'qual', 'tem', 'quanto', 'adiciona']
        if any(fp in msg_lower for fp in false_positives):
            return False

        # Negações que indicam "não quero mais" (só se carrinho não estiver vazio)
        negacoes_fechamento = ['nao', 'não', 'n', 'nope']
        if msg_lower in negacoes_fechamento:
            return True  # Será verificado se tem carrinho antes de usar

        # Confirmações simples (apenas se a mensagem for curta)
        if len(msg_lower) <= 15:  # Evita confirmar frases longas
            confirmacoes_simples = ['ok', 'certo', 'beleza', 'show', 'isso mesmo']
            return msg_lower in confirmacoes_simples

        return False

    def _detectar_nao_quer_falar_pedido(self, mensagem: str) -> bool:
        """
        Detecta se o cliente não quer falar sobre o pedido em aberto.
        Exemplos: "não quero falar sobre isso", "não quero esse pedido", "cancela", "não quero mais"
        """
        msg = self._normalizar_mensagem(mensagem)
        if not msg:
            return False
        
        # Termos que indicam que não quer falar sobre o pedido
        termos_negacao_pedido = [
            'nao quero falar',
            'nao quero esse pedido',
            'nao quero mais',
            'cancela',
            'cancelar',
            'nao quero',
            'nao preciso',
            'nao quero esse',
            'esquece',
            'esquecer',
            'nao quero esse pedido',
            'nao quero o pedido',
            'nao quero mais esse pedido',
            'nao quero mais o pedido'
        ]
        
        # Verifica se contém algum termo de negação relacionado a pedido
        for termo in termos_negacao_pedido:
            if termo in msg:
                return True
        
        return False

    def _detectar_confirmacao_cancelamento(self, mensagem: str) -> Optional[bool]:
        """
        Detecta se o cliente confirmou ou negou o cancelamento do pedido.
        Retorna True se confirmou, False se negou, None se não ficou claro.
        """
        msg = self._normalizar_mensagem(mensagem)
        if not msg:
            return None
        
        # Termos de confirmação
        termos_confirmacao = ['sim', 'pode', 'pode cancelar', 'confirma', 'confirmo', 'quero cancelar', 'cancela sim']
        # Termos de negação
        termos_negacao = ['nao', 'nao quero', 'nao cancela', 'mantem', 'mantenha', 'nao cancelar']
        
        # Verifica confirmação
        for termo in termos_confirmacao:
            if termo in msg:
                return True
        
        # Verifica negação
        for termo in termos_negacao:
            if termo in msg:
                return False
        
        return None

    async def _cancelar_pedido(self, pedido_id: Optional[int] = None, user_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Cancela um pedido.
        Trata dois casos:
        1. Pedido no schema pedidos (após checkout) - usa pedido_id
        2. Carrinho no schema chatbot (antes do checkout) - usa user_id
        
        Retorna (sucesso, mensagem)
        """
        try:
            # CASO 1: Tenta cancelar pedido no schema pedidos (após checkout)
            if pedido_id:
                from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
                from app.api.pedidos.models.model_pedido_unificado import StatusPedido
                
                pedido_repo = PedidoRepository(self.db)
                pedido = pedido_repo.get_pedido(pedido_id)
                
                if pedido:
                    # Verifica se o pedido pode ser cancelado (não pode estar entregue ou já cancelado)
                    if pedido.status == StatusPedido.ENTREGUE.value:
                        return False, "Este pedido já foi entregue e não pode ser cancelado."
                    
                    if pedido.status == StatusPedido.CANCELADO.value:
                        return False, "Este pedido já está cancelado."
                    
                    # Salva o status anterior antes de cancelar
                    status_anterior = pedido.status
                    
                    # Cancela o pedido
                    pedido.status = StatusPedido.CANCELADO.value
                    pedido_repo.db.commit()
                    
                    # Adiciona histórico
                    from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
                    pedido_repo.add_historico(
                        pedido_id=pedido_id,
                        tipo_operacao=TipoOperacaoPedido.STATUS_ALTERADO,
                        status_anterior=status_anterior,
                        status_novo=StatusPedido.CANCELADO.value,
                        descricao=f"Pedido cancelado pelo cliente via WhatsApp",
                        cliente_id=pedido.cliente_id
                    )
                    pedido_repo.db.commit()
                    
                    return True, f"Pedido #{pedido.numero_pedido} foi cancelado."
            
            # CASO 2: Se não encontrou pedido no schema pedidos, verifica carrinho no schema chatbot
            if user_id:
                try:
                    service = self._get_carrinho_service()
                    carrinho = service.obter_carrinho(user_id, self.empresa_id)
                    
                    if carrinho and carrinho.itens and len(carrinho.itens) > 0:
                        # Limpa o carrinho
                        service.limpar_carrinho(user_id, self.empresa_id)
                        return True, "Pedido em aberto (carrinho) foi cancelado."
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao verificar/limpar carrinho: {e}", exc_info=True)
            
            # Se chegou aqui, não encontrou nem pedido nem carrinho
            if pedido_id:
                return False, "Pedido não encontrado."
            elif user_id:
                return False, "Não há pedido em aberto para cancelar."
            else:
                return False, "É necessário informar pedido_id ou user_id para cancelar."
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao cancelar pedido (pedido_id={pedido_id}, user_id={user_id}): {e}", exc_info=True)
            return False, f"Erro ao cancelar pedido: {str(e)}"

    def _detectar_negacao(self, mensagem: str) -> bool:
        """Detecta se cliente disse não"""
        msg_lower = mensagem.lower().strip()
        negacoes = ['não', 'nao', 'n', 'nope', 'nunca', 'nem']
        return msg_lower in negacoes or any(msg_lower.startswith(n + ' ') for n in negacoes)

    def _detectar_pedido_cardapio(self, mensagem: str) -> bool:
        """Detecta se cliente quer ver o cardápio/produtos disponíveis"""
        msg_lower = mensagem.lower().strip()

        # Frases que indicam que cliente quer ver produtos
        frases_cardapio = [
            'quais tem', 'quais que tem', 'o que tem', 'oq tem', 'oque tem',
            'que tem ai', 'tem o que', 'tem oque', 'quais produtos',
            'quais sao', 'quais são', 'me mostra', 'mostra ai', 'mostra aí',
            'cardapio', 'cardápio', 'menu', 'lista', 'opcoes', 'opções',
            'sugestao', 'sugestão', 'sugestoes', 'sugestões', 'sugere',
            'o que voce tem', 'o que você tem', 'que voces tem', 'que vocês tem',
            'o mais', 'mais o que', 'mais oque', 'alem disso', 'além disso',
            'outras opcoes', 'outras opções', 'tem mais', 'mais alguma coisa',
            'quais as opcoes', 'quais as opções', 'ver produtos', 'quero ver'
        ]

        return any(frase in msg_lower for frase in frases_cardapio)

    def _gerar_lista_produtos(self, produtos: List[Dict], carrinho: List[Dict] = None) -> str:
        """Gera uma lista formatada de produtos para mostrar ao cliente"""
        return self.formatters.gerar_lista_produtos(produtos, carrinho)

    def _detectar_novo_endereco(self, mensagem: str) -> bool:
        """Detecta se cliente quer cadastrar novo endereço"""
        msg_lower = mensagem.lower().strip()
        palavras = ['novo', 'new', 'outro', 'cadastrar', 'adicionar', 'diferente']
        return any(p in msg_lower for p in palavras)

    def _extrair_numero(self, mensagem: str) -> Optional[int]:
        """Extrai número da mensagem"""
        msg = mensagem.strip()
        if msg.isdigit():
            return int(msg)
        # Tenta extrair primeiro número da mensagem
        match = re.search(r'\d+', msg)
        if match:
            return int(match.group())
        return None

    def _extrair_numero_natural(self, mensagem: str, max_opcoes: int = 10) -> Optional[int]:
        """
        Extrai número da mensagem, incluindo linguagem natural.
        Detecta: "primeiro", "segundo", "pode ser o 1", "esse mesmo", etc.
        """
        msg = mensagem.lower().strip()

        # Primeiro tenta extrair número direto
        numero_direto = self._extrair_numero(mensagem)
        if numero_direto and 1 <= numero_direto <= max_opcoes:
            return numero_direto

        # Mapeamento de ordinais em português
        ordinais = {
            'primeiro': 1, 'primeira': 1, '1o': 1, '1º': 1, '1a': 1, '1ª': 1,
            'segundo': 2, 'segunda': 2, '2o': 2, '2º': 2, '2a': 2, '2ª': 2,
            'terceiro': 3, 'terceira': 3, '3o': 3, '3º': 3, '3a': 3, '3ª': 3,
            'quarto': 4, 'quarta': 4, '4o': 4, '4º': 4, '4a': 4, '4ª': 4,
            'quinto': 5, 'quinta': 5, '5o': 5, '5º': 5, '5a': 5, '5ª': 5,
            'sexto': 6, 'sexta': 6,
            'setimo': 7, 'sétimo': 7, 'setima': 7, 'sétima': 7,
            'oitavo': 8, 'oitava': 8,
            'nono': 9, 'nona': 9,
            'decimo': 10, 'décimo': 10, 'decima': 10, 'décima': 10,
        }

        # Busca ordinais no texto
        for ordinal, valor in ordinais.items():
            if ordinal in msg and valor <= max_opcoes:
                return valor

        # Frases que indicam "o primeiro" / "esse mesmo"
        frases_primeiro = [
            'esse mesmo', 'essa mesma', 'esse ai', 'essa ai',
            'pode ser esse', 'pode ser essa', 'esse ta bom', 'essa ta boa',
            'o de cima', 'a de cima', 'o primeiro que apareceu'
        ]
        for frase in frases_primeiro:
            if frase in msg:
                return 1

        # Detecta "um" no contexto de seleção
        if re.search(r'\b(um|uma)\b', msg) and any(x in msg for x in ['pode ser', 'quero', 'escolho', 'manda']):
            return 1

        return None

    def _detectar_forma_pagamento_natural(self, mensagem: str) -> Optional[str]:
        """
        Detecta forma de pagamento em linguagem natural.
        Retorna: 'PIX', 'DINHEIRO', 'CARTAO' ou None
        """
        msg = mensagem.lower().strip()

        # PIX
        pix_patterns = ['pix', 'no pix', 'pelo pix', 'via pix', 'por pix', 'fazer pix']
        for pattern in pix_patterns:
            if pattern in msg:
                return 'PIX'

        # DINHEIRO
        dinheiro_patterns = [
            'dinheiro', 'em dinheiro', 'no dinheiro', 'especie', 'espécie',
            'na hora', 'pagar na hora', 'cash', 'em maos', 'em mãos'
        ]
        for pattern in dinheiro_patterns:
            if pattern in msg:
                return 'DINHEIRO'

        # CARTAO
        cartao_patterns = [
            'cartao', 'cartão', 'credito', 'crédito', 'debito', 'débito',
            'maquininha', 'na maquina', 'na máquina', 'passar cartao', 'passar cartão'
        ]
        for pattern in cartao_patterns:
            if pattern in msg:
                return 'CARTAO'

        return None

    def _parece_endereco(self, mensagem: str) -> bool:
        """Detecta se a mensagem parece ser um endereço"""
        msg_lower = mensagem.lower()
        # Palavras que indicam endereço
        indicadores = [
            'rua ', 'av ', 'av.', 'avenida', 'rod ', 'rodovia',
            'alameda', 'travessa', 'praça', 'praca', 'largo',
            'quadra', 'qd ', 'bloco', 'casa ', 'apt', 'apartamento',
            'bairro', 'centro', 'jardim', 'vila', 'parque',
            ', n', ', num', 'numero', 'número'
        ]
        # Tem número na mensagem
        tem_numero = bool(re.search(r'\d+', mensagem))
        # Tem indicador de endereço
        tem_indicador = any(ind in msg_lower for ind in indicadores)
        # Mensagem longa o suficiente
        tamanho_ok = len(mensagem) >= 10

        return (tem_numero and tem_indicador) or (tamanho_ok and tem_indicador)

    def _detectar_produto_na_mensagem(self, mensagem: str, produtos: List[Dict]) -> Optional[Dict]:
        """
        Detecta se o cliente está pedindo um produto específico
        Retorna o produto encontrado ou None
        Prioriza matches exatos sobre parciais
        """
        msg_lower = mensagem.lower()

        # Remove acentos para comparação
        def remover_acentos(texto):
            acentos = {'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
                       'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u', 'ç': 'c'}
            for acentuado, sem_acento in acentos.items():
                texto = texto.replace(acentuado, sem_acento)
            return texto

        msg_sem_acento = remover_acentos(msg_lower)

        # Palavras que indicam que cliente quer pedir algo
        verbos_pedido = ['quero', 'queria', 'me vê', 'me ve', 'pede', 'peço',
                         'manda', 'traz', 'adiciona', 'coloca', 'bota', 'da um',
                         'dá um', 'me da', 'me dá', 'vou querer', 'pode ser',
                         'vou de', 'vai de', 'um ', 'uma ', 'dois ', 'duas ',
                         'tres ', '1 ', '2 ', '3 ', '4 ', '5 ',
                         'a de ', 'o de ', 'essa', 'esse', 'aquela', 'aquele']

        tem_verbo_pedido = any(v in msg_lower for v in verbos_pedido)

        # FASE 1: Busca match EXATO do nome completo do produto
        for produto in produtos:
            nome_produto = produto['nome'].lower()
            nome_sem_acento = remover_acentos(nome_produto)

            if nome_produto in msg_lower or nome_sem_acento in msg_sem_acento:
                print(f"🎯 Match exato encontrado: {produto['nome']}")
                return produto

        # FASE 2: Busca por palavras-chave importantes (ANTES de exigir verbo!)
        # Isso permite que "coca cola" faça match mesmo sem "quero coca cola"
        palavras_genericas = ['com', 'de', 'da', 'do', 'para', 'sem', 'especial', 'grande', 'pequeno', 'pizza', 'lanche']

        # Palavras específicas de produtos (bebidas, sabores, etc)
        palavras_produto_importantes = {
            'coca': 'coca',
            'cola': 'coca',
            'coca-cola': 'coca',
            'cocacola': 'coca',
            'calabresa': 'calabresa',
            'frango': 'frango',
            'bacon': 'bacon',
            'catupiry': 'catupiry',
            'margherita': 'margherita',
            'marguerita': 'margherita',
            'burger': 'burger',
            'burguer': 'burger',
            'pepsi': 'pepsi',
            'guarana': 'guarana',
            'guaraná': 'guarana',
            'fanta': 'fanta',
            'sprite': 'sprite',
            'suco': 'suco',
            'agua': 'agua',
            'água': 'agua',
            'cerveja': 'cerveja',
            'heineken': 'heineken',
            'brahma': 'brahma',
            'skol': 'skol',
            'mussarela': 'mussarela',
            'muçarela': 'mussarela',
            'portuguesa': 'portuguesa',
            'quatro queijos': 'queijos',
            '4 queijos': 'queijos',
            'napolitana': 'napolitana',
            'batata': 'batata',
            'onion': 'onion',
            'cebola': 'cebola',
        }

        # Busca por palavras importantes (SEM exigir verbo de pedido)
        for palavra_busca, termo_produto in palavras_produto_importantes.items():
            if palavra_busca in msg_sem_acento:
                for produto in produtos:
                    nome_produto_sem_acento = remover_acentos(produto['nome'].lower())
                    if termo_produto in nome_produto_sem_acento:
                        print(f"🎯 Match por palavra-chave '{palavra_busca}': {produto['nome']}")
                        return produto

        # FASE 3: Busca por prefixos de lanches (x-alguma-coisa)
        match_x = re.search(r'x[-\s]?(\w+)', msg_lower)
        if match_x:
            termo_x = match_x.group(0).replace(' ', '-')  # normaliza "x bacon" para "x-bacon"
            for produto in produtos:
                nome_lower = produto['nome'].lower()
                if nome_lower.startswith('x-') or nome_lower.startswith('x '):
                    # Compara o termo com o nome do produto
                    nome_normalizado = nome_lower.replace(' ', '-')
                    if termo_x in nome_normalizado or nome_normalizado.startswith(termo_x):
                        print(f"🎯 Match por prefixo X-: {produto['nome']}")
                        return produto

        # Se não tem verbo de pedido, não continua para matches parciais menos específicos
        if not tem_verbo_pedido:
            return None

        # FASE 4: Busca por partes do nome (mais de 4 caracteres, não genérico)
        # Só executa se tem verbo de pedido para evitar falsos positivos
        for produto in produtos:
            nome_produto = produto['nome'].lower()
            nome_sem_acento_prod = remover_acentos(nome_produto)
            palavras_produto = nome_sem_acento_prod.split()
            for palavra in palavras_produto:
                if len(palavra) > 4 and palavra not in palavras_genericas:
                    if palavra in msg_sem_acento:
                        print(f"🎯 Match parcial por '{palavra}': {produto['nome']}")
                        return produto

        return None

    def _get_carrinho_service(self) -> CarrinhoService:
        # Mantém a assinatura original, mas delega para o Domain Service
        return self.carrinho_domain.get_carrinho_service()

    def _obter_carrinho_db(self, user_id: str):
        return self.carrinho_domain.obter_carrinho_db(user_id)

    def _verificar_carrinho_aberto(self, user_id: str) -> Optional[Any]:
        """
        Verifica se existe um carrinho temporário em aberto para o usuário.
        Retorna o carrinho se existir, None caso contrário.
        """
        return self.carrinho_domain.verificar_carrinho_aberto(user_id)

    def _formatar_mensagem_carrinho_aberto(self, carrinho_resp) -> str:
        """
        Formata mensagem informando sobre o carrinho em aberto.
        """
        return self.carrinho_domain.formatar_mensagem_carrinho_aberto(carrinho_resp)

    def _detectar_confirmacao_cancelamento_carrinho(self, mensagem: str) -> Optional[bool]:
        """
        Detecta se o cliente quer cancelar o carrinho em aberto.
        Retorna True se confirmou cancelamento, False se não quer cancelar, None se não ficou claro.
        """
        msg = self._normalizar_mensagem(mensagem)
        if not msg:
            return None
        
        termos_cancelar = [
            "cancelar", "cancela", "cancel", "desistir", "desist",
            "nao quero", "não quero", "nao quero mais", "não quero mais",
            "fazer novo", "novo pedido", "começar de novo", "comecar de novo",
            "limpar", "apagar", "deletar", "remover tudo"
        ]
        
        termos_continuar = [
            "continuar", "seguir", "manter", "quero continuar",
            "quero esse", "esse mesmo", "esse pedido", "manter esse",
            "sim", "ok", "pode", "claro", "vamos", "bora", "isso mesmo",
            "quero adicionar", "adicionar mais", "mais alguma coisa",
            "quero mais", "adiciona", "adicionar"
        ]
        
        if any(termo in msg for termo in termos_cancelar):
            return True
        if any(termo in msg for termo in termos_continuar):
            return False
        return None

    def _carrinho_response_para_lista(self, carrinho_resp) -> List[Dict]:
        return self.carrinho_domain.carrinho_response_para_lista(carrinho_resp)

    def _sincronizar_carrinho_dados(self, user_id: str, dados: Dict) -> Tuple[Optional[Any], List[Dict]]:
        return self.carrinho_domain.sincronizar_carrinho_dados(user_id, dados)

    def _montar_item_carrinho_request(self, produto: Dict, quantidade: int):
        return self.carrinho_domain.montar_item_carrinho_request(produto, quantidade)

    def _detectar_confirmacao_adicao(self, mensagem: str) -> Optional[bool]:
        msg = self._normalizar_mensagem(mensagem)
        if not msg:
            return None
        positivos = [
            "sim", "ok", "pode", "pode adicionar", "adiciona", "adicionar",
            "claro", "isso", "isso mesmo", "pode sim", "bora", "vamos"
        ]
        negativos = [
            "nao", "não", "cancelar", "cancela", "deixa", "deixa pra la",
            "deixa pra lá", "não quero", "nao quero"
        ]
        if any(p in msg for p in positivos):
            return True
        if any(n in msg for n in negativos):
            return False
        return None

    async def _adicionar_endereco_ao_pedido(
        self,
        user_id: str,
        dados: Dict,
        endereco_pendente: Dict[str, Any]
    ) -> str:
        """
        Adiciona endereço ao pedido/carrinho após calcular taxa de entrega.
        Verifica se o endereço já existe para o cliente, se não existir cadastra,
        e vincula ao carrinho/pedido atual.
        """
        try:
            # Cria ou obtém o cliente
            cliente = self.address_service.get_cliente_by_telefone(user_id)
            if not cliente:
                # Cria cliente se não existir
                cliente = self.address_service.criar_cliente_se_nao_existe(user_id)
                if not cliente:
                    return "❌ Não foi possível criar seu cadastro. Por favor, tente novamente."

            cliente_id = cliente["id"]

            # Verifica se o endereço já existe para este cliente
            logradouro = endereco_pendente.get('logradouro')
            numero = endereco_pendente.get('numero')
            bairro = endereco_pendente.get('bairro')
            cidade = endereco_pendente.get('cidade')
            estado = endereco_pendente.get('estado')
            cep = endereco_pendente.get('cep')

            # Busca endereço existente
            query_existente = text("""
                SELECT id, logradouro, numero, complemento, bairro, cidade, estado,
                       cep, ponto_referencia, latitude, longitude, is_principal
                FROM cadastros.enderecos
                WHERE cliente_id = :cliente_id
                  AND logradouro = :logradouro
                  AND numero = :numero
                  AND bairro = :bairro
                  AND cidade = :cidade
                  AND estado = :estado
                  AND cep = :cep
                LIMIT 1
            """)
            result = self.db.execute(query_existente, {
                "cliente_id": cliente_id,
                "logradouro": logradouro,
                "numero": numero,
                "bairro": bairro,
                "cidade": cidade,
                "estado": estado,
                "cep": cep
            }).fetchone()

            endereco_id = None
            endereco_formatado = endereco_pendente.get('endereco_formatado', '')

            if result:
                # Endereço já existe - usa o ID existente
                endereco_id = result[0]
                print(f"✅ Endereço já cadastrado encontrado - ID: {endereco_id}")
            else:
                # Endereço não existe - cadastra novo
                dados_endereco = {
                    "logradouro": logradouro,
                    "numero": numero,
                    "complemento": endereco_pendente.get('complemento'),
                    "bairro": bairro,
                    "cidade": cidade,
                    "estado": estado,
                    "cep": cep,
                    "latitude": endereco_pendente.get('latitude'),
                    "longitude": endereco_pendente.get('longitude'),
                }
                
                endereco_salvo = self.address_service.criar_endereco_cliente(
                    user_id,
                    dados_endereco,
                    is_principal=False  # Não marca como principal automaticamente
                )

                if endereco_salvo:
                    endereco_id = endereco_salvo['id']
                    print(f"✅ Novo endereço cadastrado - ID: {endereco_id}")
                else:
                    return "❌ Não foi possível cadastrar o endereço. Por favor, tente novamente."

            # Obtém ou cria o carrinho
            service = self._get_carrinho_service()
            tipo_entrega = dados.get("tipo_entrega") or "DELIVERY"
            carrinho = service.obter_ou_criar_carrinho(
                user_id=user_id,
                empresa_id=self.empresa_id,
                tipo_entrega=tipo_entrega
            )

            # Atualiza o carrinho com o endereço_id
            carrinho.endereco_id = endereco_id
            carrinho.tipo_entrega = tipo_entrega
            self.db.commit()
            self.db.refresh(carrinho)

            # Atualiza os dados da conversa
            dados['endereco_id'] = endereco_id
            dados['endereco_texto'] = endereco_formatado
            dados['tipo_entrega'] = tipo_entrega

            # Sincroniza o carrinho nos dados
            self._sincronizar_carrinho_dados(user_id, dados)

            # Retorna mensagem de sucesso
            msg = f"✅ *Endereço adicionado ao pedido!*\n\n"
            msg += f"📍 {endereco_formatado}\n\n"
            msg += "O que você gostaria de pedir? 😊"

            return msg

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao adicionar endereço ao pedido: {e}", exc_info=True)
            return "❌ Não foi possível adicionar o endereço ao pedido. Por favor, tente novamente."

    def _adicionar_ao_carrinho(self, user_id: str, dados: Dict, produto: Dict, quantidade: int = 1):
        """
        Adiciona um produto ao carrinho usando o banco de dados
        """
        return self.carrinho_domain.adicionar_ao_carrinho(user_id, dados, produto, quantidade)

    def _personalizar_item_carrinho(
        self,
        dados: Dict,
        acao: str,
        item_nome: str,
        produto_busca: str = None
    ) -> Tuple[bool, str]:
        """
        Personaliza um item no carrinho (remove ingrediente ou adiciona extra)
        Funciona tanto com carrinho quanto com pedido_contexto (modo conversacional)

        Args:
            dados: Dados da conversa com carrinho ou pedido_contexto
            acao: 'remover_ingrediente' ou 'adicionar_extra'
            item_nome: Nome do ingrediente/adicional
            produto_busca: Nome do produto (opcional, usa último adicionado)

        Returns:
            (sucesso, mensagem)
        """
        return self.carrinho_domain.personalizar_item_carrinho(dados, acao, item_nome, produto_busca)

    def _detectar_remocao_produto(self, mensagem: str) -> bool:
        """Detecta se o cliente quer remover um produto do carrinho"""
        msg_lower = mensagem.lower()

        verbos_remocao = [
            'tirar', 'tira', 'remover', 'remove', 'retirar', 'retira',
            'cancelar', 'cancela', 'nao quero', 'não quero', 'sem',
            'desistir', 'desisto', 'tira o', 'tira a', 'remove o', 'remove a'
        ]

        return any(verbo in msg_lower for verbo in verbos_remocao)

    def _detectar_ver_carrinho(self, mensagem: str) -> bool:
        """Detecta se o cliente quer ver o carrinho"""
        msg_lower = mensagem.lower()

        frases_carrinho = [
            'ver carrinho', 'meu carrinho', 'o que tem no carrinho',
            'o que eu pedi', 'meu pedido', 'ver pedido', 'resumo',
            'quanto ta', 'quanto tá', 'quanto está', 'total',
            'o que tem', 'mostrar carrinho', 'mostrar pedido'
        ]

        return any(frase in msg_lower for frase in frases_carrinho)

    def _remover_do_carrinho(self, user_id: str, dados: Dict, produto: Dict, quantidade: int = None) -> Tuple[bool, str, Optional[Any], List[Dict]]:
        """
        Remove um produto do carrinho
        Returns: (sucesso, mensagem)
        """
        return self.carrinho_domain.remover_do_carrinho(user_id, dados, produto, quantidade)

    def _formatar_carrinho(self, carrinho: List[Dict]) -> str:
        """Formata o carrinho para exibição, incluindo personalizações"""
        return self.formatters.formatar_carrinho(carrinho)

    def _extrair_quantidade(self, mensagem: str) -> int:
        """Extrai quantidade da mensagem, padrão é 1"""
        msg_lower = mensagem.lower()

        # Mapeamento de números por extenso
        numeros = {
            'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'três': 3,
            'quatro': 4, 'cinco': 5, 'seis': 6, 'meia duzia': 6, 'meia dúzia': 6
        }

        for palavra, valor in numeros.items():
            if palavra in msg_lower:
                return valor

        # Tenta encontrar número
        match = re.search(r'(\d+)\s*(x|un|uni)', msg_lower)
        if match:
            return int(match.group(1))

        match = re.search(r'^(\d+)\s', msg_lower)
        if match:
            return int(match.group(1))

        return 1

    def _detectar_entrega(self, mensagem: str) -> bool:
        """Detecta se cliente escolheu ENTREGA"""
        msg_lower = mensagem.lower().strip()
        palavras_entrega = [
            'entrega', 'entregar', 'delivery', 'casa', 'em casa',
            'minha casa', 'no meu endereço', 'levar', 'manda',
            '1', 'um', 'primeira'
        ]
        return any(p in msg_lower for p in palavras_entrega)

    def _detectar_retirada(self, mensagem: str) -> bool:
        """Detecta se cliente escolheu RETIRADA"""
        msg_lower = mensagem.lower().strip()
        palavras_retirada = [
            'retirar', 'retirada', 'buscar', 'pegar', 'na loja',
            'no local', 'vou buscar', 'vou pegar', 'pickup',
            '2', 'dois', 'segunda'
        ]
        return any(p in msg_lower for p in palavras_retirada)

    # ========== FLUXO DE CADASTRO RÁPIDO DE CLIENTE (durante pedido) ==========

    def _detectar_se_nao_e_nome(self, mensagem: str) -> bool:
        """
        Detecta se a mensagem NÃO parece ser um nome válido.
        Retorna True se NÃO for um nome, False se pode ser um nome.
        """
        import re

        mensagem_lower = (mensagem or "").lower().strip()

        # Heurística: limpa pontuação, emojis e palavras de cortesia antes das checagens,
        # pois clientes costumam responder "João Silva, obrigado" e isso não deve invalidar o nome.
        cleaned = re.sub(r'[^\w\s]', ' ', mensagem_lower, flags=re.UNICODE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Remove palavras de cortesia comuns para evitar falsos positivos
        cortesias = {"obrigado", "obrigada", "valeu", "ok", "obg", "brigado", "brigada", "tudo bem", "até", "ate", "tchau"}
        tokens = [t for t in cleaned.split() if t and t not in cortesias]
        cleaned_lower = " ".join(tokens)

        # Heurística rápida: perguntas comuns sem "?"
        if mensagem_lower.startswith(("voces", "vocês", "vc", "vcs", "você", "voce")):
            return True

        # Lista de palavras/frases que indicam que NÃO é um nome (checadas no texto limpo)
        palavras_nao_nome = [
            "chamar", "atendente", "humano", "falar com", "quero falar",
            "preciso de", "ligar atendente", "chama alguém", "oi", "olá",
            "bom dia", "boa tarde", "boa noite", "e aí",
            "estão atendendo", "estao atendendo", "vocês estão", "voce esta",
            "você está", "voces estao", "atendendo", "atendem", "atende",
            "sim", "não", "nao", "tudo certo", "beleza", "blz",
            "quero", "gostaria", "preciso", "tem", "você tem", "voce tem",
            "quanto", "qual", "onde", "como", "quando", "por favor",
            # Dúvidas comuns que aparecem muito no WhatsApp (sem "?")
            "entrega", "entregam", "entregue", "delivery", "retirada", "retirar",
            "taxa", "frete", "cardápio", "cardapio", "menu", "promoção", "promocao",
            "horário", "horario", "aberto", "fechado", "abre", "fecha",
            "endereço", "endereco", "localização", "localizacao",
        ]

        # Se o texto limpo contém palavras que indicam que não é um nome -> não é nome
        if any(palavra in cleaned_lower for palavra in palavras_nao_nome):
            return True

        # Se for uma pergunta explícita, não é nome
        if "?" in mensagem:
            return True

        # Verifica se tem verbos comuns que não aparecem em nomes (no texto limpo)
        verbos_comuns = [
            "está", "esta", "estão", "estao", "é", "e", "são", "sao",
            "tem", "têm", "tem", "faz", "fazem", "quer", "querem",
            "precisa", "precisam", "gosta", "gostam", "vai", "vão", "vao"
        ]
        partes = cleaned_lower.split()
        if any(verbo in partes for verbo in verbos_comuns):
            return True

        # Verifica se tem números (nomes geralmente não têm números)
        if any(char.isdigit() for char in cleaned_lower):
            return True

        # Se passou todas as verificações, pode ser um nome
        return False

    async def _processar_cadastro_nome_rapido(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa o nome do cliente durante o cadastro rápido
        Se a mensagem não for um nome válido, responde ao cliente primeiro e depois pede o nome novamente
        """
        import logging
        logger = logging.getLogger(__name__)

        nome = mensagem.strip()
        # Tenta extrair nome quando o usuário responde em uma frase (ex: "Meu nome é João", "Me chamo João")
        try:
            import re
            m = re.search(r'(?:meu nome é|meu nome e|me chamo(?: é)?|sou|chamo(?: me)?|meu nome:)\s+(.+)', nome, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                # Remove pontuação final/excessos
                extracted = re.sub(r'^[^\w\d]+|[^\w\d]+$', '', extracted)
                if extracted:
                    nome = extracted
        except Exception:
            # Não falha por causa da heurística de extração
            pass

        logger.debug(f"[cadastro_nome] Iniciando processamento do nome. user_id={user_id!r}, mensagem={mensagem!r}, dados_keys={list(dados.keys())}, nome_extraido={nome!r}")

        # Validação básica de tamanho
        if len(nome) < 2:
            logger.debug(f"[cadastro_nome] Nome muito curto: {nome!r} (user_id={user_id})")
            return "❓ Nome muito curto! Por favor, digite seu nome completo 😊"
        
        # Detecta se NÃO é um nome válido
        if self._detectar_se_nao_e_nome(nome):
            # Não é um nome - responde ao cliente primeiro usando IA conversacional
            logger.info(f"[cadastro_nome] Mensagem não parece ser um nome: {nome!r} - respondendo e pedindo nome novamente (user_id={user_id})")
            
            # Gera resposta conversacional para a mensagem do cliente
            try:
                todos_produtos = self._buscar_todos_produtos()
                carrinho = dados.get('carrinho', [])
                
                # Responde ao cliente de forma natural
                resposta_ia = await self._gerar_resposta_conversacional(
                    user_id=user_id,
                    mensagem=mensagem,
                    tipo_conversa="resposta_generica",
                    contexto="Cliente respondeu algo que não é um nome durante cadastro",
                    produtos=todos_produtos,
                    carrinho=carrinho,
                    dados=dados
                )
                
                # Mantém o estado de cadastro e pede o nome novamente
                logger.debug(f"[cadastro_nome] Mantendo estado cadastro_nome para user_id={user_id}")
                self._salvar_estado_conversa(user_id, STATE_CADASTRO_NOME, dados)
                
                # Combina a resposta da IA com a solicitação do nome
                mensagem_completa = f"{resposta_ia}\n\n"
                mensagem_completa += "━━━━━━━━━━━━━━━━━━━━\n\n"
                mensagem_completa += "Para continuar, preciso do seu *nome completo* 😊\n\n"
                mensagem_completa += "Como você gostaria de ser chamado?"
                
                logger.debug(f"[cadastro_nome] Enviando resposta conversacional + pedido de nome (user_id={user_id})")
                return mensagem_completa
                
            except Exception as e:
                print(f"⚠️ Erro ao gerar resposta conversacional: {e}")
                # Fallback: resposta simples + pedido de nome
                self._salvar_estado_conversa(user_id, STATE_CADASTRO_NOME, dados)
                return f"Entendi! 😊\n\nMas para continuar, preciso do seu *nome completo*.\n\nComo você gostaria de ser chamado?"
        
            # Validação: prefere nome completo, mas aceita também nome simples para não bloquear o fluxo.
        partes_nome = nome.split()
        if len(partes_nome) < 2:
                # Mantém a flag de cadastro rápido mas permite salvar nomes de uma palavra
                dados.setdefault('nome_incompleto', True)
                logger.debug(f"[cadastro_nome] Nome com 1 palavra aceito temporariamente: {nome!r} (user_id={user_id})")
                # não retorna aqui — prossegue para tentativa de salvar o nome informado
        
        # Parece ser um nome válido - tenta salvar
        try:
            # Usa o address_service para criar/atualizar cliente (garante consistência)
            logger.info(f"[cadastro_nome] Tentando criar/atualizar cliente: telefone={user_id}, nome={nome!r}")
            cliente = self.address_service.criar_cliente_se_nao_existe(
                telefone=user_id,
                nome=nome
            )

            if not cliente:
                logger.warning(f"[cadastro_nome] address_service.criar_cliente_se_nao_existe retornou None (user_id={user_id}, nome={nome})")
                # Mantém o estado de cadastro em caso de erro
                self._salvar_estado_conversa(user_id, STATE_CADASTRO_NOME, dados)
                return "❌ Ops! Ocorreu um erro ao salvar seu nome. Tente novamente 😊"
            
            # Nome salvo - remove flag de cadastro e continua com o fluxo normal
            dados.pop('cadastro_rapido', None)
            logger.info(f"[cadastro_nome] ✅ Cliente cadastrado/atualizado: id={cliente.get('id')} nome={cliente.get('nome')!r} telefone={cliente.get('telefone')}")
            # limpa sinal de nome_incompleto se existir
            dados.pop('nome_incompleto', None)
            
            # Se estava no meio de um pedido, continua com o fluxo de pedido
            if dados.get('carrinho') or dados.get('tipo_entrega'):
                return self._perguntar_entrega_ou_retirada(user_id, dados)
            
            # Verifica se aceita pedidos pelo WhatsApp
            config = self._get_chatbot_config()
            if config and not config.aceita_pedidos_whatsapp:
                # Não aceita pedidos - envia link do cardápio
                link_cardapio = self._obter_link_cardapio()
                if config.mensagem_redirecionamento:
                    mensagem_boas_vindas = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                else:
                    mensagem_boas_vindas = f"✅ *Perfeito, {nome}!*\n\n"
                    mensagem_boas_vindas += "📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n"
                    mensagem_boas_vindas += f"👉 {link_cardapio}\n\n"
                    mensagem_boas_vindas += "Depois é só fazer seu pedido pelo site! 😊"
                
                # Volta para o estado de conversação normal
                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                return mensagem_boas_vindas
            
            # Caso contrário, volta para o estado de conversação normal e pergunta sobre pedidos
            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
            
            mensagem_boas_vindas = f"✅ *Perfeito, {nome}!*\n\n"
            mensagem_boas_vindas += "Agora posso te ajudar! 😊\n\n"
            mensagem_boas_vindas += "O que você gostaria de pedir hoje?"
            
            return mensagem_boas_vindas
            
        except Exception as e:
            print(f"❌ Erro ao salvar nome do cliente: {e}")
            import traceback
            traceback.print_exc()
            # Mantém o estado de cadastro em caso de erro
            self._salvar_estado_conversa(user_id, STATE_CADASTRO_NOME, dados)
            return "❌ Ops! Ocorreu um erro ao salvar seu nome. Tente novamente 😊"

    def _buscar_produtos(self, termo_busca: str = "") -> List[Dict[str, Any]]:
        """Busca produtos no banco de dados usando SQL direto"""
        return self.produto_service.buscar_produtos(termo_busca)

    def _buscar_promocoes(self) -> List[Dict[str, Any]]:
        """Busca produtos em promoção/destaque usando SQL direto (prioriza receitas)"""
        return self.produto_service.buscar_promocoes()

    def _obter_estado_conversa(self, user_id: str) -> Tuple[str, Dict[str, Any]]:
        """Obtém estado salvo da conversa (delegado para `ConversacaoService`)."""
        return self.conversacao_service.obter_estado(user_id)

    def _salvar_estado_conversa(self, user_id: str, estado: str, dados: Dict[str, Any]):
        """Salva estado da conversa (delegado para `ConversacaoService`)."""
        self.conversacao_service.salvar_estado(user_id, estado, dados)

    def _buscar_todos_produtos(self) -> List[Dict[str, Any]]:
        """Busca TODOS os produtos disponíveis no banco usando SQL direto (produtos + receitas)"""
        return self.produto_service.buscar_todos_produtos()

    def _normalizar_termo_busca(self, termo: str) -> str:
        """
        Normaliza termo de busca removendo acentos, espaços extras e caracteres especiais.
        """
        return self.produto_service.normalizar_termo_busca(termo)

    def _corrigir_termo_busca(self, termo: str, lista_referencia: List[str], threshold: float = 0.6) -> str:
        """
        Corrige erros de digitação usando difflib.
        Exemplo: "te hmburg" -> "hamburg"
        """
        return self.produto_service.corrigir_termo_busca(termo, lista_referencia, threshold)

    def _expandir_sinonimos(self, termo: str) -> List[str]:
        """
        Expande termo com sinônimos e variações comuns.
        Exemplo: "hamburg" -> ["hamburg", "hamburger", "burger", "hamburguer"]
        """
        return self.produto_service.expandir_sinonimos(termo)

    def _buscar_produtos_inteligente(self, termo_busca: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Busca inteligente em produtos, receitas e combos com:
        - Correção de erros de digitação
        - Suporte a variações (burger/hamburg)
        - Busca rápida e otimizada
        - Limitada para escalabilidade
        
        Args:
            termo_busca: Termo digitado pelo cliente (pode ter erros)
            limit: Limite de resultados (padrão 5 para ser rápido)
        
        Returns:
            Lista de produtos encontrados (produtos + receitas + combos)
        """
        return self.produto_service.buscar_produtos_inteligente(termo_busca, limit)

    def _montar_contexto(self, user_id: str, mensagem: str, estado: str, dados: Dict) -> Tuple[str, List[Dict]]:
        """
        Monta o contexto com dados do banco para o LLM
        Retorna: (contexto_sistema, historico_mensagens)
        """
        carrinho = dados.get('carrinho', [])
        historico = dados.get('historico', [])[-6:]  # Últimas 6 mensagens

        # SEMPRE busca TODOS os produtos do banco para dar contexto completo ao LLM
        todos_produtos = self._buscar_todos_produtos()

        # Monta contexto do sistema
        contexto_sistema = SALES_SYSTEM_PROMPT + f"""

=== CARDÁPIO COMPLETO (TODOS OS PRODUTOS DISPONÍVEIS) ===
IMPORTANTE: Estes são os ÚNICOS produtos que existem. NÃO INVENTE outros!

"""
        if todos_produtos:
            for i, p in enumerate(todos_produtos, 1):
                contexto_sistema += f"{i}. {p['nome']} - R$ {p['preco']:.2f}\n"
        else:
            contexto_sistema += "Nenhum produto cadastrado.\n"

        contexto_sistema += f"""
CARRINHO ATUAL DO CLIENTE:
"""
        if carrinho:
            total = 0
            for item in carrinho:
                preco_adicionais = item.get('personalizacoes', {}).get('preco_adicionais', 0.0)
                subtotal = (item['preco'] + preco_adicionais) * item.get('quantidade', 1)
                total += subtotal
                contexto_sistema += f"- {item.get('quantidade', 1)}x {item['nome']} = R$ {subtotal:.2f}\n"
            contexto_sistema += f"TOTAL: R$ {total:.2f}\n"
        else:
            contexto_sistema += "Carrinho vazio\n"

        # Adiciona informação sobre estado atual
        contexto_sistema += f"""
ESTADO ATUAL: {estado}
"""

        contexto_sistema += """
=== REGRAS OBRIGATÓRIAS - LEIA COM ATENÇÃO ===
1. SOMENTE USE OS PRODUTOS E PREÇOS LISTADOS ACIMA - são os únicos que existem!
2. NÃO INVENTE produtos, preços, tamanhos ou variações
3. Se o cliente pedir algo que NÃO está na lista, diga "Não temos esse produto"
4. Cada produto tem UM preço fixo - não existe pequeno/médio/grande
5. Seja NATURAL e breve (2-3 frases)
6. Use máximo 1-2 emojis
7. NUNCA diga que é IA/robô

⛔ PROIBIÇÕES ABSOLUTAS - NUNCA FAÇA ISSO:
- NUNCA peça número de cartão, CVV, data de validade ou dados bancários
- NUNCA peça CPF, RG ou documentos
- NUNCA diga "seu pedido foi confirmado" ou "está a caminho"
- NUNCA colete endereço (o sistema faz isso automaticamente)
- NUNCA pergunte forma de pagamento (o sistema faz isso automaticamente)
- NUNCA finalize o pedido você mesma
- NUNCA invente itens no carrinho que o cliente não pediu

✅ O QUE VOCÊ DEVE FAZER:
- Ajudar o cliente a escolher produtos do cardápio
- Responder perguntas sobre os produtos
- Perguntar "Quer mais alguma coisa?" após adicionar um produto
- Se o cliente quiser fechar, diga apenas: "Show! Quer mais alguma coisa ou posso fechar o pedido?"

O SISTEMA VAI AUTOMATICAMENTE cuidar de: entrega/retirada, endereço, pagamento e confirmação.
Sua única função é ajudar a ESCOLHER PRODUTOS. Nada mais!
"""

        # Salva produtos no estado
        dados['produtos_disponiveis'] = todos_produtos

        # Adiciona mensagem atual ao histórico (evita duplicar quando já veio do banco)
        if not historico or historico[-1].get("role") != "user" or historico[-1].get("content") != mensagem:
            historico.append({"role": "user", "content": mensagem})
        dados['historico'] = historico

        return contexto_sistema, historico

    # ========== FLUXO DE ENDEREÇOS ==========

    async def _iniciar_fluxo_endereco(self, user_id: str, dados: Dict) -> str:
        """
        Inicia o fluxo de endereço verificando se cliente tem endereços salvos
        """
        print(f"📍 Iniciando fluxo de endereço para {user_id}")

        # Buscar endereços existentes do cliente
        enderecos = self.address_service.get_enderecos_cliente(user_id)

        if enderecos:
            # Cliente tem endereços salvos - mostrar opções
            dados['enderecos_salvos'] = enderecos
            self._salvar_estado_conversa(user_id, STATE_LISTANDO_ENDERECOS, dados)

            mensagem = "📍 *ENDEREÇO DE ENTREGA*\n"
            mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
            mensagem += "Você tem endereços salvos:\n\n"
            mensagem += self.address_service.formatar_lista_enderecos_para_chat(enderecos)
            mensagem += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
            mensagem += "📌 Digite o *número* do endereço (ex: 1, 2, 3...)\n"
            mensagem += "🆕 Ou digite *NOVO* para cadastrar outro endereço"

            return mensagem
        else:
            # Cliente não tem endereços - pedir para digitar direto
            self._salvar_estado_conversa(user_id, STATE_BUSCANDO_ENDERECO_GOOGLE, dados)

            mensagem = "📍 *ENDEREÇO DE ENTREGA*\n"
            mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
            mensagem += "Para onde vamos entregar?\n\n"
            mensagem += "Digite seu endereço completo:\n"
            mensagem += "• Rua e número\n"
            mensagem += "• Bairro\n"
            mensagem += "• Cidade\n\n"
            mensagem += "_Exemplo: Rua das Flores 123 Centro Brasília_"

            return mensagem

    async def _processar_selecao_endereco_salvo(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa a escolha do cliente: usar endereço salvo ou cadastrar novo
        Aceita números diretos ou linguagem natural (ex: "pode ser o primeiro")
        Também detecta se o usuário digitou um endereço diretamente
        """
        # Cliente quer cadastrar novo endereço
        if self._detectar_novo_endereco(mensagem):
            self._salvar_estado_conversa(user_id, STATE_BUSCANDO_ENDERECO_GOOGLE, dados)

            return "📍 Ok! Vamos cadastrar um novo endereço.\n\nDigite seu endereço completo:\n_Exemplo: Rua das Flores, 123, Centro, São Paulo_"

        enderecos = dados.get('enderecos_salvos', [])

        # Cliente escolheu um número (endereço salvo) - agora aceita linguagem natural
        numero = self._extrair_numero_natural(mensagem, max_opcoes=len(enderecos))
        if numero:
            if numero < 1 or numero > len(enderecos):
                return f"Ops! Digite um número de 1 a {len(enderecos)}, ou *NOVO* para cadastrar outro 😊"

            # Selecionar endereço
            endereco_selecionado = enderecos[numero - 1]
            dados['endereco_selecionado'] = endereco_selecionado
            dados['endereco_texto'] = endereco_selecionado['endereco_completo']
            dados['endereco_id'] = endereco_selecionado['id']

            # Ir para pagamento (ou resumo se já foi detectado)
            msg_endereco = "✅ *Endereço selecionado!*\n"
            msg_endereco += "━━━━━━━━━━━━━━━━━━━━\n\n"
            msg_endereco += f"📍 {endereco_selecionado['endereco_completo']}\n\n"
            
            return await self._ir_para_pagamento_ou_resumo(
                user_id, dados,
                msg_endereco
            )

        # Verifica se o usuário digitou um endereço diretamente (ao invés de número)
        if self._parece_endereco(mensagem):
            # Trata como se fosse busca de novo endereço
            self._salvar_estado_conversa(user_id, STATE_BUSCANDO_ENDERECO_GOOGLE, dados)
            return await self._processar_busca_endereco_google(user_id, mensagem, dados)

        # Não entendeu a resposta
        return "Não entendi 😅\nDigite o *número* do endereço (ex: \"1\" ou \"primeiro\") ou *NOVO* para cadastrar outro"

    async def _processar_busca_endereco_google(self, user_id: str, texto_endereco: str, dados: Dict) -> str:
        """
        Busca endereço via API /api/localizacao/buscar-endereco e mostra 3 opções
        Se API não retornar resultados, aceita endereço manual
        """
        # Validação básica
        if len(texto_endereco) < 5:
            return "Hmm, esse endereço tá muito curto 🤔\nTenta colocar mais detalhes, tipo rua, número e bairro"

        print(f"🔍 Buscando endereço via API: {texto_endereco}")

        # Buscar via API /api/localizacao/buscar-endereco (retorna 3 resultados)
        enderecos_google = self.address_service.buscar_enderecos_google(texto_endereco, max_results=3)

        if not enderecos_google:
            # Fallback: aceitar endereço manual se API não retornar resultados
            print("⚠️ API não retornou resultados, aceitando endereço manual")

            # Salvar endereço digitado como o endereço selecionado
            endereco_manual = {
                "index": 1,
                "endereco_completo": texto_endereco,
                "logradouro": texto_endereco,
                "numero": None,
                "bairro": None,
                "cidade": None,
                "estado": None,
                "cep": None,
                "latitude": None,
                "longitude": None
            }
            dados['endereco_google_selecionado'] = endereco_manual

            # Ir para complemento
            self._salvar_estado_conversa(user_id, STATE_COLETANDO_COMPLEMENTO, dados)

            return f"✅ Endereço: *{texto_endereco}*\n\nTem algum *complemento*?\n_Ex: Apartamento 101, Bloco B, Casa dos fundos_\n\nSe não tiver, digite *NAO*"

        # Salvar opções encontradas
        dados['enderecos_google'] = enderecos_google
        self._salvar_estado_conversa(user_id, STATE_SELECIONANDO_ENDERECO_GOOGLE, dados)

        # Formatar mensagem com as opções
        mensagem = "🔍 *Encontrei esses endereços:*\n\n"
        for end in enderecos_google:
            mensagem += f"*{end['index']}.* {end['endereco_completo']}\n\n"

        mensagem += "📌 *É um desses?* Digite o número (1, 2 ou 3)\n"
        mensagem += "❌ Ou digite *NAO* para digitar outro endereço"

        return mensagem

    async def _processar_selecao_endereco_google(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa a seleção do endereço do Google Maps
        Aceita números ou linguagem natural (ex: "pode ser o primeiro")
        """
        msg_lower = mensagem.lower().strip()

        # Cliente quer tentar de novo
        if msg_lower in ['nao', 'não', 'n', 'outro', 'nenhum', 'tentar', 'nova busca', 'errado', 'nenhum desses', 'nenhuma']:
            self._salvar_estado_conversa(user_id, STATE_BUSCANDO_ENDERECO_GOOGLE, dados)
            return "Ok! Digite o endereço completo novamente:\n_Exemplo: Rua das Flores, 123, Centro, São Paulo_"

        enderecos_google = dados.get('enderecos_google', [])

        # Cliente escolheu um número - agora aceita linguagem natural
        numero = self._extrair_numero_natural(mensagem, max_opcoes=len(enderecos_google))
        if numero:
            if numero < 1 or numero > len(enderecos_google):
                return f"Digite um número de 1 a {len(enderecos_google)} 😊"

            # Selecionar endereço do Google
            endereco_selecionado = enderecos_google[numero - 1]
            dados['endereco_google_selecionado'] = endereco_selecionado

            # Perguntar complemento
            self._salvar_estado_conversa(user_id, STATE_COLETANDO_COMPLEMENTO, dados)

            return f"✅ Endereço: *{endereco_selecionado['endereco_completo']}*\n\nTem algum *complemento*?\n_Ex: Apartamento 101, Bloco B, Casa dos fundos_\n\nSe não tiver, digite *NAO*"

        # Não entendeu
        return "Digite o *número* do endereço (1, 2 ou 3) ou *NAO* para digitar outro endereço"

    async def _processar_complemento(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa o complemento do endereço e salva
        """
        msg_lower = mensagem.lower().strip()
        endereco_google = dados.get('endereco_google_selecionado', {})

        # Definir complemento
        complemento = None
        if msg_lower not in ['nao', 'não', 'n', 'nenhum', 'sem complemento', '-']:
            complemento = mensagem.strip()

        # Montar dados do endereço para salvar
        dados_endereco = {
            "logradouro": endereco_google.get("logradouro"),
            "numero": endereco_google.get("numero"),
            "complemento": complemento,
            "bairro": endereco_google.get("bairro"),
            "cidade": endereco_google.get("cidade"),
            "estado": endereco_google.get("estado"),
            "cep": endereco_google.get("cep"),
            "latitude": endereco_google.get("latitude"),
            "longitude": endereco_google.get("longitude")
        }

        # Criar cliente se não existir e salvar endereço
        cliente = self.address_service.criar_cliente_se_nao_existe(user_id)

        if cliente:
            # Salvar endereço no banco
            endereco_salvo = self.address_service.criar_endereco_cliente(
                user_id,
                dados_endereco,
                is_principal=True
            )

            if endereco_salvo:
                dados['endereco_selecionado'] = endereco_salvo
                dados['endereco_id'] = endereco_salvo['id']

        # Montar endereço completo para exibição
        endereco_completo = endereco_google.get('endereco_completo', '')
        if complemento:
            endereco_completo += f" - {complemento}"

        dados['endereco_texto'] = endereco_completo

        # Ir para pagamento (ou resumo se já foi detectado)
        msg_endereco = "✅ *Endereço salvo!*\n"
        msg_endereco += "━━━━━━━━━━━━━━━━━━━━\n\n"
        msg_endereco += f"📍 {endereco_completo}\n\n"
        
        return await self._ir_para_pagamento_ou_resumo(
            user_id, dados,
            msg_endereco
        )

    def _mensagem_formas_pagamento(self) -> str:
        """Retorna a mensagem de formas de pagamento baseada no banco de dados"""
        meios = self._buscar_meios_pagamento()
        return self.pagamento_domain.formatar_mensagem_formas_pagamento(meios)

    async def _ir_para_pagamento_ou_resumo(self, user_id: str, dados: Dict, mensagem_prefixo: str = "") -> str:
        """
        Verifica se o pagamento já foi detectado antecipadamente.
        Se sim, pula direto para o resumo do pedido.
        Se não, pergunta a forma de pagamento.
        """
        if dados.get('forma_pagamento') and dados.get('meio_pagamento_id'):
            # Pagamento já foi detectado! Pular direto para resumo
            forma = dados.get('forma_pagamento')
            print(f"💳 Pagamento já detectado ({forma}), pulando para resumo!")
            return await self._gerar_resumo_pedido(user_id, dados)
        else:
            # Perguntar forma de pagamento
            self._salvar_estado_conversa(user_id, STATE_COLETANDO_PAGAMENTO, dados)
            return mensagem_prefixo + self._mensagem_formas_pagamento()

    # ========== FLUXO ENTREGA/RETIRADA ==========

    def _perguntar_entrega_ou_retirada(self, user_id: str, dados: Dict) -> str:
        """
        Pergunta ao cliente se é para entrega ou retirada
        Verifica se o cliente está cadastrado (tem nome completo), se não, pede o nome primeiro
        """
        # Verifica se o cliente está cadastrado (tem nome completo, não apenas "Cliente WhatsApp")
        cliente = self.address_service.get_cliente_by_telefone(user_id)
        nome_cliente = cliente.get('nome', '') if cliente else ''
        
        # Se não está cadastrado ou tem apenas nome genérico, pede o nome primeiro
        if not cliente or nome_cliente in ['Cliente WhatsApp', 'Cliente', ''] or len(nome_cliente.split()) < 2:
            # Inicia cadastro rápido - pede apenas o nome
            dados['cadastro_rapido'] = True  # Flag para indicar que é cadastro rápido durante pedido
            self._salvar_estado_conversa(user_id, STATE_CADASTRO_NOME, dados)
            
            msg = "👋 *Olá! Antes de finalizar seu pedido, preciso do seu nome completo*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += "Como você gostaria de ser chamado?\n\n"
            msg += "Digite seu *nome completo*:"
            
            return msg
        
        # Cliente já está cadastrado - pergunta entrega/retirada normalmente
        self._salvar_estado_conversa(user_id, STATE_PERGUNTANDO_ENTREGA_RETIRADA, dados)
        
        # Mostra resumo rápido do pedido antes de perguntar
        carrinho = dados.get('carrinho', [])
        if carrinho:
            total = sum((item['preco'] + item.get('personalizacoes', {}).get('preco_adicionais', 0.0)) * item.get('quantidade', 1) for item in carrinho)
            msg = f"📦 *Resumo do pedido:*\n"
            for item in carrinho:
                qtd = item.get('quantidade', 1)
                msg += f"• {qtd}x {item['nome']}\n"
            msg += f"\n💰 *Total: R$ {total:.2f}*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        else:
            msg = ""

        msg += "🚚 *Como você prefere receber?*\n\n"
        msg += "1️⃣ *Entrega* 🏍️\n"
        msg += "   Levamos até você!\n\n"
        msg += "2️⃣ *Retirada* 🏪\n"
        msg += "   Você busca aqui na loja\n\n"
        msg += "Digite *1* para entrega ou *2* para retirada 😊"
        
        return msg

    async def _processar_entrega_ou_retirada(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa a escolha do cliente entre entrega ou retirada
        """
        if self._detectar_entrega(mensagem):
            # Cliente quer ENTREGA - iniciar fluxo de endereço
            dados['tipo_entrega'] = 'ENTREGA'
            print("🏍️ Cliente escolheu ENTREGA, iniciando fluxo de endereço")
            return await self._iniciar_fluxo_endereco(user_id, dados)

        elif self._detectar_retirada(mensagem):
            # Cliente quer RETIRADA - pular endereço, ir para pagamento
            dados['tipo_entrega'] = 'RETIRADA'
            dados['endereco_texto'] = 'Retirada na loja'

            print("🏪 Cliente escolheu RETIRADA, indo para pagamento")
            
            # Mensagem bonita de confirmação
            msg_retirada = "✅ *Retirada na loja selecionada!*\n"
            msg_retirada += "━━━━━━━━━━━━━━━━━━━━\n\n"
            msg_retirada += "🏪 Você vai buscar aqui conosco\n"
            msg_retirada += "   Sem taxa de entrega! 😊\n\n"
            
            return await self._ir_para_pagamento_ou_resumo(
                user_id, dados,
                msg_retirada
            )

        else:
            # Não entendeu
            return "❓ Não entendi 😅\n\nDigite *1* para entrega ou *2* para retirada na loja 😊"

    async def _processar_pagamento(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa a forma de pagamento escolhida
        Aceita números ou linguagem natural baseado nos meios de pagamento do banco
        """
        meios = self._buscar_meios_pagamento()

        # Primeiro tenta detectar por linguagem natural usando o método dinâmico
        meio_detectado = self._detectar_forma_pagamento_em_mensagem(mensagem)
        if meio_detectado:
            dados['forma_pagamento'] = meio_detectado['nome']
            dados['meio_pagamento_id'] = meio_detectado['id']
            print(f"💳 Pagamento detectado (natural): {meio_detectado['nome']} (ID: {meio_detectado['id']})")
            return await self._gerar_resumo_pedido(user_id, dados)

        # Tenta por número (incluindo ordinais)
        numero = self._extrair_numero_natural(mensagem, max_opcoes=len(meios))

        if numero and 1 <= numero <= len(meios):
            meio_selecionado = meios[numero - 1]
            dados['forma_pagamento'] = meio_selecionado['nome']
            dados['meio_pagamento_id'] = meio_selecionado['id']
            print(f"💳 Pagamento selecionado (número): {meio_selecionado['nome']} (ID: {meio_selecionado['id']})")
            return await self._gerar_resumo_pedido(user_id, dados)

        # Mensagem de erro com opções dinâmicas
        opcoes_str = "\n".join([f"*{i+1}* - {meio['nome']}" for i, meio in enumerate(meios)])
        nomes_str = ", ".join([f"*{meio['nome'].lower()}*" for meio in meios[:3]])  # Mostra até 3 exemplos

        return f"❓ Não entendi 😅\n\nEscolha uma das opções:\n{opcoes_str}\n\nOu digite diretamente: {nomes_str} 😊"

    async def _gerar_resumo_pedido(self, user_id: str, dados: Dict) -> str:
        """Gera o resumo final do pedido"""
        carrinho = dados.get('carrinho', [])
        endereco = dados.get('endereco_texto', 'Não informado')
        forma_pagamento = dados.get('forma_pagamento', 'PIX')
        tipo_entrega = dados.get('tipo_entrega', 'ENTREGA')

        if not carrinho:
            return "Ops, seu carrinho está vazio! Me diz o que você quer pedir 😊"

        # Calcular totais (incluindo preco_adicionais)
        subtotal = 0
        for item in carrinho:
            preco_adicionais = item.get('personalizacoes', {}).get('preco_adicionais', 0.0)
            subtotal += (item['preco'] + preco_adicionais) * item.get('quantidade', 1)

        # Taxa de entrega só para delivery
        if tipo_entrega == 'RETIRADA':
            taxa_entrega = 0.0
        else:
            taxa_entrega = 5.00  # TODO: Calcular baseado na distância

        total = subtotal + taxa_entrega

        # Salvar preview
        dados['preview'] = {
            'subtotal': subtotal,
            'taxa_entrega': taxa_entrega,
            'total': total
        }
        self._salvar_estado_conversa(user_id, STATE_CONFIRMANDO_PEDIDO, dados)

        # Montar mensagem bonita e dinâmica
        mensagem = "📋 *RESUMO DO SEU PEDIDO*\n"
        mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        mensagem += "🛒 *ITENS:*\n"
        for idx, item in enumerate(carrinho, 1):
            qtd = item.get('quantidade', 1)
            preco_adicionais = item.get('personalizacoes', {}).get('preco_adicionais', 0.0)
            subtotal_item = (item['preco'] + preco_adicionais) * qtd
            mensagem += f"*{idx}. {qtd}x {item['nome']}*\n"
            mensagem += f"   R$ {subtotal_item:.2f}\n"
            
            # Mostra personalizações se houver
            personalizacoes = item.get('personalizacoes', {})
            removidos = personalizacoes.get('removidos', [])
            adicionais = personalizacoes.get('adicionais', [])
            
            if removidos:
                mensagem += f"   🚫 Sem: {', '.join(removidos)}\n"
            
            if adicionais:
                for add in adicionais:
                    if isinstance(add, dict):
                        nome = add.get('nome', add)
                        preco = add.get('preco', 0)
                        if preco and preco > 0:
                            mensagem += f"            ➕ {nome} (+R$ {preco:.2f})\n"
                        else:
                            mensagem += f"            ➕ {nome}\n"
                    else:
                        mensagem += f"            ➕ {add}\n"
            
            mensagem += "\n"

        mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Mostrar tipo de entrega/retirada
        if tipo_entrega == 'RETIRADA':
            mensagem += "🏪 *RETIRADA NA LOJA*\n"
            mensagem += "   Você busca aqui conosco\n\n"
        else:
            mensagem += "📍 *ENTREGA*\n"
            mensagem += f"   {endereco}\n\n"

        mensagem += f"💳 *PAGAMENTO*\n"
        mensagem += f"   {forma_pagamento}\n\n"
        
        mensagem += "━━━━━━━━━━━━━━━━━━━━\n"
        mensagem += f"Subtotal: R$ {subtotal:.2f}\n"
        if taxa_entrega > 0:
            mensagem += f"taxa de entrega: {taxa_entrega:.2f}\n"
        mensagem += f"\n💰 *TOTAL: R$ {total:.2f}*\n"
        mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"

        mensagem += "✅ Digite *OK* para confirmar\n"
        mensagem += "❌ Ou *CANCELAR* para desistir"

        return mensagem

    async def _salvar_pedido_via_checkout(self, user_id: str, dados: Dict) -> Optional[int]:
        """
        Salva o pedido chamando o endpoint /checkout via HTTP
        Usa o carrinho temporário do banco de dados (schema chatbot)

        Args:
            user_id: Telefone do cliente (WhatsApp)
            dados: Dados da conversa com carrinho, endereço, etc

        Returns:
            ID do pedido criado ou None se falhar
        """
        try:
            # Importa serviço de carrinho
            from app.api.chatbot.services.service_carrinho import CarrinhoService
            from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
            from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
            from app.api.catalogo.adapters.receitas_adapter import ReceitasAdapter
            from app.api.catalogo.adapters.combo_adapter import ComboAdapter
            
            # Cria serviço de carrinho
            produto_contract = ProdutoAdapter(self.db)
            complemento_contract = ComplementoAdapter(self.db)
            receitas_contract = ReceitasAdapter(self.db)
            combo_contract = ComboAdapter(self.db)
            
            carrinho_service = CarrinhoService(
                db=self.db,
                produto_contract=produto_contract,
                complemento_contract=complemento_contract,
                receitas_contract=receitas_contract,
                combo_contract=combo_contract
            )
            
            # Busca carrinho do banco de dados
            carrinho = carrinho_service.obter_carrinho(user_id, self.empresa_id)
            if not carrinho:
                print("[Checkout] Carrinho vazio ou não encontrado no banco")
                return None
            
            # Buscar ou criar cliente para obter o super_token e cliente_id
            cliente = self.address_service.criar_cliente_se_nao_existe(user_id)
            if not cliente:
                print("[Checkout] ERRO: Não foi possível criar/buscar cliente")
                return None

            super_token = cliente.get('super_token')
            cliente_id = cliente.get('id')
            if not super_token:
                print("[Checkout] ERRO: Cliente sem super_token")
                return None
            if not cliente_id:
                print("[Checkout] ERRO: Cliente sem ID")
                return None

            # Converte carrinho do banco para formato do checkout
            from app.api.chatbot.repositories.repo_carrinho import CarrinhoRepository
            from app.api.chatbot.models.model_carrinho import CarrinhoTemporarioModel
            
            carrinho_repo = CarrinhoRepository(self.db)
            carrinho_model = carrinho_repo.get_by_id(carrinho.id, load_items=True)
            if not carrinho_model:
                print("[Checkout] ERRO: Carrinho não encontrado após busca")
                return None
            
            # Converte carrinho passando cliente_id para garantir que sempre tenha
            payload = carrinho_service.converter_para_checkout(carrinho_model, cliente_id=cliente_id)
            
            # Adiciona meio de pagamento se foi detectado
            meio_pagamento_id = dados.get('meio_pagamento_id') or carrinho_model.meio_pagamento_id
            if meio_pagamento_id:
                total = float(carrinho_model.valor_total)
                payload["meios_pagamento"] = [{
                    "id": meio_pagamento_id,
                    "valor": total
                }]
                print(f"[Checkout] Meio de pagamento (ID: {meio_pagamento_id}), Valor: R$ {total:.2f}")

            print(f"[Checkout] Payload: {json.dumps(payload, indent=2, default=str)}")

            # Chamar endpoint /checkout
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Content-Type": "application/json",
                    "X-Super-Token": super_token
                }

                # URL do checkout (localhost pois estamos no mesmo servidor)
                checkout_url = "http://localhost:8000/api/pedidos/client/checkout"

                print(f"[Checkout] Chamando {checkout_url}")
                response = await client.post(checkout_url, json=payload, headers=headers)

                print(f"[Checkout] Status: {response.status_code}")

                if response.status_code == 201:
                    result = response.json()
                    pedido_id = result.get('id')
                    print(f"[Checkout] ✅ Pedido criado com sucesso! ID: {pedido_id}")
                    
                    # Limpa o carrinho após sucesso no checkout
                    carrinho_service.limpar_carrinho(user_id, self.empresa_id)
                    print(f"[Checkout] ✅ Carrinho limpo após criação do pedido")
                    
                    return pedido_id
                else:
                    # Extrair mensagem de erro da resposta
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', 'Erro desconhecido')
                    except:
                        error_detail = response.text

                    print(f"[Checkout] ❌ Erro ao criar pedido: {response.status_code} - {error_detail}")
                    return {"erro": True, "mensagem": error_detail}

        except httpx.TimeoutException:
            print("[Checkout] ⏰ Timeout ao chamar endpoint /checkout")
            return {"erro": True, "mensagem": "Tempo esgotado ao processar pedido. Tente novamente."}
        except Exception as e:
            print(f"[Checkout] ❌ ERRO ao salvar pedido via checkout: {e}")
            import traceback
            traceback.print_exc()
            return {"erro": True, "mensagem": "Erro interno ao processar pedido."}


    # ========== RESPOSTAS CONVERSACIONAIS ==========

    async def _nao_entendeu_mensagem(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Quando o chatbot não entende a mensagem:
        1. Envia notificação para WhatsApp da empresa
        2. Envia mensagem para cliente com link do cardápio
        3. Desativa o chatbot para esse cliente
        """
        from . import database as chatbot_db
        from sqlalchemy import text, bindparam
        from app.utils.telefone import variantes_telefone_para_busca, normalizar_telefone_para_armazenar
        
        # Busca nome do cliente (em transação separada para evitar problemas)
        cliente_nome = None
        try:
            # Faz rollback de qualquer transação anterior que possa ter falhado
            self.db.rollback()
            
            candidatos = variantes_telefone_para_busca(user_id)
            if not candidatos:
                telefone_canon = normalizar_telefone_para_armazenar(user_id)
                candidatos = [telefone_canon or user_id]

            cliente_query = (
                text(
                    """
                    SELECT nome
                    FROM cadastros.clientes
                    WHERE telefone IN :telefones
                    LIMIT 1
                    """
                )
                .bindparams(bindparam("telefones", expanding=True))
            )
            result = self.db.execute(cliente_query, {"telefones": candidatos})
            cliente_row = result.fetchone()
            if cliente_row:
                cliente_nome = cliente_row[0]
        except Exception as e:
            print(f"⚠️ Erro ao buscar nome do cliente: {e}")
            # Faz rollback e continua
            try:
                self.db.rollback()
            except:
                pass
        
        # Monta mensagem de notificação para empresa
        mensagem_notificacao = f"🔔 *Chatbot não entendeu mensagem*\n\n"
        mensagem_notificacao += f"O chatbot não conseguiu entender a mensagem do cliente.\n\n"
        mensagem_notificacao += f"📱 *Cliente:* {cliente_nome or user_id}\n"
        mensagem_notificacao += f"💬 *Mensagem:* {mensagem}\n"
        mensagem_notificacao += f"🏢 *Empresa ID:* {self.empresa_id}\n\n"
        mensagem_notificacao += f"⚠️ O chatbot foi desativado para este cliente. Entre em contato para atendê-lo."
        
        # Envia notificação para empresa (em try separado para garantir execução)
        notificacao_enviada = False
        try:
            # Faz rollback de qualquer transação anterior
            self.db.rollback()
            
            # Busca display_phone_number da configuração do WhatsApp da empresa
            from app.api.notifications.repositories.whatsapp_config_repository import WhatsAppConfigRepository
            repo_whatsapp = WhatsAppConfigRepository(self.db)
            config_whatsapp = repo_whatsapp.get_active_by_empresa(str(self.empresa_id))
            
            if config_whatsapp and config_whatsapp.display_phone_number:
                from ..core.notifications import OrderNotification
                from ..core.config_whatsapp import format_phone_number
                
                notifier = OrderNotification()
                empresa_phone = format_phone_number(config_whatsapp.display_phone_number)
                
                result = await notifier.send_whatsapp_message(
                    empresa_phone, 
                    mensagem_notificacao, 
                    empresa_id=str(self.empresa_id)
                )
                
                if result.get("success"):
                    print(f"✅ Notificação enviada para empresa {self.empresa_id} - telefone: {empresa_phone}")
                    notificacao_enviada = True
                else:
                    print(f"⚠️ Falha ao enviar notificação: {result.get('error')}")
        except Exception as e:
            print(f"⚠️ Erro ao enviar notificação para empresa: {e}")
            import traceback
            traceback.print_exc()
            # Faz rollback e continua
            try:
                self.db.rollback()
            except:
                pass
        
        # Desativa chatbot para este cliente (em try separado)
        try:
            # Faz rollback de qualquer transação anterior
            self.db.rollback()
            
            # PAUSA O CHATBOT POR 3 HORAS quando pausa por conta própria
            destrava_em = chatbot_db.get_auto_pause_until()
            chatbot_db.set_bot_status(
                self.db,
                user_id,
                paused_by="sistema_nao_entendeu",
                empresa_id=self.empresa_id,
                desativa_chatbot_em=destrava_em,
            )
            # Commit da desativação
            self.db.commit()
            print(f"✅ Chatbot desativado para cliente {user_id} por {chatbot_db.AUTO_PAUSE_HOURS} horas (chatbot_destrava_em: {destrava_em})")
        except Exception as e:
            print(f"⚠️ Erro ao desativar chatbot: {e}")
            import traceback
            traceback.print_exc()
            # Faz rollback e continua
            try:
                self.db.rollback()
            except:
                pass
        
        # Mensagem para o cliente:
        # Quando não entendemos e pausamos, direcionamos para o cardápio (evita pedir nome/dados aqui).
        try:
            link_cardapio = self._obter_link_cardapio()
        except Exception:
            link_cardapio = "https://chatbot.mensuraapi.com.br"

        mensagem_cliente = (
            "Desculpe, não consegui entender sua mensagem. 😔\n\n"
            "Para fazer seu pedido, acesse nosso cardápio:\n"
            f"👉 {link_cardapio}\n\n"
            "Se precisar de ajuda, digite *chamar atendente*."
        )
        
        # Salva no histórico (sem commit para não interferir)
        try:
            historico = dados.get('historico', [])
            historico.append({"role": "user", "content": mensagem})
            historico.append({"role": "assistant", "content": mensagem_cliente})
            dados['historico'] = historico[-10:]
            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
        except Exception as e:
            print(f"⚠️ Erro ao salvar histórico: {e}")
        
        return mensagem_cliente

    async def _enviar_notificacao_chamar_atendente(self, user_id: str, dados: Dict):
        """
        Envia notificação para a empresa quando cliente pede para chamar atendente.
        Usa WebSocket para notificar o dashboard/frontend em tempo real.
        """
        from sqlalchemy import text, bindparam
        from app.utils.telefone import variantes_telefone_para_busca, normalizar_telefone_para_armazenar
        
        # Busca nome do cliente
        cliente_nome = None
        try:
            self.db.rollback()
            candidatos = variantes_telefone_para_busca(user_id)
            if not candidatos:
                telefone_canon = normalizar_telefone_para_armazenar(user_id)
                candidatos = [telefone_canon or user_id]

            cliente_query = (
                text(
                    """
                    SELECT nome
                    FROM cadastros.clientes
                    WHERE telefone IN :telefones
                    LIMIT 1
                    """
                )
                .bindparams(bindparam("telefones", expanding=True))
            )
            result = self.db.execute(cliente_query, {"telefones": candidatos})
            cliente_row = result.fetchone()
            if cliente_row:
                cliente_nome = cliente_row[0]
        except Exception as e:
            print(f"⚠️ Erro ao buscar nome do cliente: {e}")
            try:
                self.db.rollback()
            except:
                pass
        
        # Monta dados da notificação
        notification_data = {
            "cliente_phone": user_id,
            "cliente_nome": cliente_nome,
            "tipo": "chamar_atendente",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Envia notificação via WebSocket para o dashboard
        try:
            from ..core.notifications import send_chatbot_websocket_notification
            
            title = "🔔 Solicitação de Atendimento Humano"
            message = f"Cliente {cliente_nome or user_id} está solicitando atendimento de um humano.\n\n📱 Telefone: {user_id}"
            if cliente_nome:
                message += f"\n👤 Nome: {cliente_nome}"
            
            sent_count = await send_chatbot_websocket_notification(
                empresa_id=self.empresa_id,
                notification_type="chamar_atendente",
                title=title,
                message=message,
                data=notification_data
            )
            
            if sent_count > 0:
                print(f"✅ Notificação WebSocket enviada para empresa {self.empresa_id} - {sent_count} conexão(ões) ativa(s)")
            else:
                print(f"⚠️ Notificação WebSocket enviada mas nenhuma conexão ativa para empresa {self.empresa_id}")
                
        except Exception as e:
            print(f"⚠️ Erro ao enviar notificação WebSocket: {e}")
            import traceback
            traceback.print_exc()
        
        # Tenta também salvar no sistema de notificações (opcional)
        try:
            from app.api.notifications.services.notification_service import NotificationService
            from app.api.notifications.schemas.notification_schemas import NotificationCreate
            
            notification_service = NotificationService(self.db)
            
            notification_create = NotificationCreate(
                empresa_id=str(self.empresa_id),
                user_id=None,  # Notificação para a empresa, não para um usuário específico
                notification_type="chatbot_chamar_atendente",
                title="Solicitação de Atendimento Humano",
                message=f"Cliente {cliente_nome or user_id} está solicitando atendimento de um humano",
                data=notification_data,
                channels=["in_app"]  # Apenas notificação interna
            )
            
            await notification_service.create_notification(notification_create)
            print(f"✅ Notificação salva no banco de dados para empresa {self.empresa_id}")
            
        except Exception as e:
            print(f"⚠️ Erro ao salvar notificação no banco: {e}")
            # Não é crítico, continua mesmo se falhar

    async def _gerar_resposta_conversacional(
        self,
        user_id: str,
        mensagem: str,
        tipo_conversa: str,
        contexto: str,
        produtos: List[Dict],
        carrinho: List[Dict],
        dados: Dict
    ) -> str:
        """
        Gera resposta conversacional natural usando a IA.
        É o coração do bot humanizado - conversa como pessoa real!
        """
        # Monta histórico recente para dar contexto real
        historico = dados.get('historico', [])
        linhas_historico = []
        for msg in historico[-6:]:
            role = "Cliente" if msg.get("role") == "user" else "Atendente"
            content = (msg.get("content") or "").strip()
            if content:
                linhas_historico.append(f"{role}: {content}")
        historico_texto = "\n".join(linhas_historico) if linhas_historico else "Sem histórico"

        # Monta prompt conversacional
        prompt_conversa = f"""Você é um atendente simpático de delivery via WhatsApp.
Responda de forma NATURAL, CURTA (1-3 frases) e AMIGÁVEL. Use no máximo 1 emoji.

CONTEXTO:
- Tipo de conversa: {tipo_conversa}
- Carrinho do cliente: {len(carrinho)} itens, R$ {sum(i['preco']*i.get('quantidade',1) for i in carrinho):.2f}
- Histórico recente:
{historico_texto}

REGRAS:
1. NUNCA mostre o cardápio completo (a menos que peçam explicitamente "cardápio")
2. Para "o que tem?", "tem o que?" → Responda algo como "Temos pizzas, lanches e bebidas! Quer uma sugestão ou prefere ver o cardápio?"
3. Para saudações → Seja simpático e pergunte o que a pessoa quer
4. Para perguntas vagas → Dê uma sugestão rápida de 1-2 produtos populares
5. Para "não sei" → Ajude sugerindo algo
6. NUNCA peça dados pessoais, cartão, CPF etc
7. Seja BREVE - máximo 2-3 linhas

PRODUTOS DISPONÍVEIS (para referência, NÃO liste todos):
{', '.join([p['nome'] for p in produtos[:10]])}

Mensagem do cliente: "{mensagem}"

Responda de forma natural e curta:"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": prompt_conversa},
                        {"role": "user", "content": mensagem}
                    ],
                    "temperature": 0.8,  # Mais criatividade
                    "max_tokens": 150,   # Respostas curtas
                }

                # Verifica se a chave API está configurada
                if not GROQ_API_KEY or not GROQ_API_KEY.strip():
                    print("⚠️ GROQ_API_KEY não configurada - usando fallback inteligente")
                    raise ValueError("GROQ_API_KEY não configurada")
                
                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
                    "Content-Type": "application/json"
                }

                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    resposta = result["choices"][0]["message"]["content"].strip()

                    # Limpa respostas muito longas
                    if len(resposta) > 300:
                        resposta = resposta[:300] + "..."

                    # Salva no histórico (evita duplicar quando já veio do banco)
                    historico = dados.get('historico', [])
                    if not historico or historico[-1].get("role") != "user" or historico[-1].get("content") != mensagem:
                        historico.append({"role": "user", "content": mensagem})
                    historico.append({"role": "assistant", "content": resposta})
                    dados['historico'] = historico[-10:]
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)

                    return resposta

        except Exception as e:
            print(f"❌ Erro na conversa: {e}")

        # Se chegou aqui, não conseguiu gerar resposta adequada - trata como não entendido
        return await self._nao_entendeu_mensagem(user_id, mensagem, dados)

    async def _gerar_resposta_sobre_produto(
        self,
        user_id: str,
        produto: Dict,
        pergunta: str,
        dados: Dict
    ) -> str:
        """
        Gera resposta sobre um produto específico.
        Usa a descrição da receita que contém os ingredientes!
        """
        try:
            nome_produto = produto.get('nome', '')
            tipo_produto = produto.get('tipo', 'produto')
            produto_id = produto.get('id', '')
            
            print(f"🔍 Buscando descrição para: '{nome_produto}' (tipo: {tipo_produto}, id: {produto_id})")
            
            # Se for uma receita (tem prefixo "receita_"), extrai o ID
            receita_id = None
            if tipo_produto == 'receita' or (isinstance(produto_id, str) and produto_id.startswith('receita_')):
                try:
                    receita_id = int(produto_id.replace('receita_', ''))
                    print(f"   📝 É uma receita, ID extraído: {receita_id} (produto_id original: {produto_id})")
                except Exception as e:
                    print(f"   ⚠️ Erro ao extrair ID da receita: {e} (produto_id: {produto_id})")
                    receita_id = None
            
            # Detecta se a pergunta original era sobre ingredientes ou preço
            pergunta_lower = pergunta.lower() if pergunta else ""
            eh_pergunta_ingredientes = any(palavra in pergunta_lower for palavra in [
                'que vem', 'que tem', 'ingredientes', 'composição', 'feito', 'feita'
            ])
            eh_pergunta_preco = any(palavra in pergunta_lower for palavra in [
                'quanto fica', 'quanto que fica', 'quanto custa', 'quanto que custa',
                'qual o preço', 'qual preço', 'quanto é', 'preço', 'valor'
            ])
            
            # Se foi pergunta sobre PREÇO, responde diretamente
            if eh_pergunta_preco:
                quantidade = self._extrair_quantidade_pergunta(pergunta, nome_produto)
                if quantidade > 1:
                    total = produto['preco'] * quantidade
                    msg = f"💰 *{nome_produto}* - {quantidade}x R$ {produto['preco']:.2f} = R$ {total:.2f}\n\n"
                else:
                    msg = f"💰 *{nome_produto}* - R$ {produto['preco']:.2f}\n\n"
                msg += self._obter_mensagem_final_pedido()
                return msg
            
            # PRIMEIRO: Busca a descrição da receita (que contém os ingredientes)
            descricao_receita = None
            receita_id_para_busca = receita_id
            
            # Se não tem receita_id, tenta buscar pelo nome ou extrair do produto_id
            if not receita_id_para_busca:
                if tipo_produto == 'receita' and isinstance(produto_id, str) and 'receita_' in produto_id:
                    try:
                        receita_id_para_busca = int(produto_id.replace('receita_', ''))
                    except Exception as e:
                        print(f"   ⚠️ Erro ao extrair ID da receita: {e}")
                
                # Se ainda não tem receita_id, tenta buscar pelo nome
                if not receita_id_para_busca:
                    try:
                        from sqlalchemy import text
                        query = text("""
                            SELECT id, descricao 
                            FROM catalogo.receitas
                            WHERE nome ILIKE :nome 
                            AND empresa_id = :empresa_id
                            LIMIT 1
                        """)
                        result = self.db.execute(query, {
                            "nome": f"%{nome_produto}%",
                            "empresa_id": self.empresa_id
                        }).fetchone()
                        
                        if result:
                            receita_id_para_busca = result[0]
                            descricao_receita = result[1]
                            print(f"   ✅ Receita encontrada pelo nome (ID: {receita_id_para_busca})")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao buscar receita pelo nome: {e}")
            
            # Busca descrição pelo ID da receita
            if receita_id_para_busca and not descricao_receita:
                try:
                    from sqlalchemy import text
                    query = text("""
                        SELECT descricao 
                        FROM catalogo.receitas
                        WHERE id = :receita_id AND empresa_id = :empresa_id
                        LIMIT 1
                    """)
                    result = self.db.execute(query, {
                        "receita_id": receita_id_para_busca,
                        "empresa_id": self.empresa_id
                    }).fetchone()
                    if result and result[0]:
                        descricao_receita = result[0]
                        print(f"   📝 Descrição encontrada no banco: {descricao_receita[:50]}...")
                except Exception as e:
                    print(f"   ⚠️ Erro ao buscar descrição da receita: {e}")
            
            # Monta resposta usando a descrição
            msg = f"*{nome_produto}* - R$ {produto['preco']:.2f}\n\n"
            
            if descricao_receita:
                # Usa a descrição que contém os ingredientes
                msg += f"{descricao_receita}\n\n"
                print(f"   ✅ Resposta gerada usando descrição da receita")
            elif produto.get('descricao'):
                # Fallback: usa descrição do produto se disponível
                msg += f"{produto['descricao']}\n\n"
                print(f"   ✅ Resposta gerada usando descrição do produto")
            else:
                # Se não encontrou descrição, informa
                if eh_pergunta_ingredientes:
                    msg += "😅 No momento não tenho informações sobre os ingredientes deste produto.\n\n"
                else:
                    msg += "😊 Este produto está disponível! Quer saber mais alguma coisa?\n\n"
            
            # Adiciona adicionais disponíveis se houver receita_id
            if receita_id_para_busca:
                try:
                    adicionais = self.ingredientes_service.buscar_adicionais_receita(receita_id_para_busca)
                    if adicionais:
                        msg += "➕ *Adicionais disponíveis:*\n"
                        for add in adicionais[:4]:  # Mostra até 4 adicionais
                            msg += f"• {add['nome']} (+R$ {add['preco']:.2f})\n"
                        msg += "\n"
                except Exception as e:
                    print(f"   ⚠️ Erro ao buscar adicionais: {e}")
            
            msg += self._obter_mensagem_final_pedido()
            return msg
        except Exception as e:
            print(f"❌ Erro ao buscar ingredientes de {produto.get('nome', 'produto')}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback básico - detecta se era pergunta de preço
            pergunta_lower = pergunta.lower() if pergunta else ""
            eh_pergunta_preco = any(palavra in pergunta_lower for palavra in [
                'quanto fica', 'quanto que fica', 'quanto custa', 'quanto que custa',
                'qual o preço', 'qual preço', 'quanto é', 'preço', 'valor'
            ])
            
            if eh_pergunta_preco:
                msg = f"💰 *{produto['nome']}* - R$ {produto['preco']:.2f}\n\n"
                msg += self._obter_mensagem_final_pedido()
            else:
                msg = f"*{produto['nome']}* - R$ {produto['preco']:.2f}\n\n"
                msg += self._obter_mensagem_final_pedido()
            return msg

    async def _calcular_e_responder_taxa_entrega(
        self,
        user_id: str,
        endereco: str,
        dados: Dict
    ) -> str:
        """
        Calcula e retorna a taxa de entrega para o cliente.
        Se tiver endereço, busca no Google Maps e mostra o endereço formatado.
        Salva o endereço encontrado no contexto para permitir adicionar ao pedido depois.
        """
        try:
            from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel
            from sqlalchemy import or_

            # Se tiver endereço, busca no Google Maps
            endereco_formatado = None
            endereco_encontrado = None
            if endereco and len(endereco.strip()) > 5:
                print(f"🔍 Buscando endereço no Google Maps: {endereco}")
                enderecos_google = self.address_service.buscar_enderecos_google(endereco, max_results=1)
                
                if enderecos_google and len(enderecos_google) > 0:
                    endereco_encontrado = enderecos_google[0]
                    endereco_formatado = endereco_encontrado.get('endereco_completo', endereco)
                    print(f"✅ Endereço encontrado: {endereco_formatado}")
                    
                    # Salva o endereço encontrado no contexto para permitir adicionar ao pedido depois
                    dados['endereco_pendente_adicao'] = {
                        'endereco_formatado': endereco_formatado,
                        'logradouro': endereco_encontrado.get('logradouro'),
                        'numero': endereco_encontrado.get('numero'),
                        'complemento': endereco_encontrado.get('complemento'),
                        'bairro': endereco_encontrado.get('bairro'),
                        'cidade': endereco_encontrado.get('cidade'),
                        'estado': endereco_encontrado.get('estado'),
                        'cep': endereco_encontrado.get('cep'),
                        'latitude': endereco_encontrado.get('latitude'),
                        'longitude': endereco_encontrado.get('longitude'),
                    }
                else:
                    print(f"⚠️ Endereço não encontrado no Google Maps, usando endereço original")
                    endereco_formatado = endereco

            # Busca a primeira região de entrega ativa (taxa padrão)
            # TODO: Se tiver coordenadas do endereço, calcular distância e usar região específica
            regiao = self.db.query(RegiaoEntregaModel).filter(
                and_(
                    RegiaoEntregaModel.empresa_id == self.empresa_id,
                    RegiaoEntregaModel.ativo == True
                )
            ).order_by(RegiaoEntregaModel.distancia_max_km.asc()).first()

            if regiao:
                taxa = float(regiao.taxa_entrega)
                tempo_estimado = regiao.tempo_estimado_min or 30
            else:
                # Fallback se não tiver região configurada
                taxa = 5.0
                tempo_estimado = 30

            # Monta resposta
            msg = "🚚 *Taxa de Entrega*\n\n"
            
            if endereco_formatado:
                msg += f"📍 *Endereço encontrado:*\n{endereco_formatado}\n\n"
            
            msg += f"💰 *Valor:* R$ {taxa:.2f}\n"
            msg += f"⏱️ *Tempo estimado:* {tempo_estimado} minutos\n\n"
            
            msg += self._obter_mensagem_final_pedido()
            
            # Salva no histórico
            historico = dados.get('historico', [])
            historico.append({"role": "user", "content": f"Pergunta sobre taxa de entrega{f' para {endereco}' if endereco else ''}"})
            dados['historico'] = historico
            self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
            
            return msg

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao calcular taxa de entrega: {e}", exc_info=True)
            return "Desculpe, não consegui calcular a taxa de entrega no momento. Entre em contato conosco para mais informações! 😊"

    # ========== PROCESSAMENTO PRINCIPAL ==========

    async def processar_mensagem(self, user_id: str, mensagem: str, pedido_aberto: Optional[Dict[str, Any]] = None) -> str:
        """
        Processa mensagem usando Groq API com fluxo de endereços integrado
        """
        # FASE 4: Inicializa observabilidade para este user_id
        if not self.observability or self.observability.user_id != user_id:
            self.observability = ChatbotObservability(self.empresa_id, user_id)
        
        try:
            # Obtém estado atual
            estado, dados = self._obter_estado_conversa(user_id)
            print(f"📊 Estado atual: {estado}")
            print(f"💬 Mensagem recebida (user_id={user_id}): {mensagem}")
            msg_lower = (mensagem or "").lower()

            # Prioridade absoluta: "chamar atendente" deve furar QUALQUER estado (inclusive cadastro de nome).
            # Caso contrário, quando o cliente clica no botão em meio ao STATE_CADASTRO_NOME,
            # o fluxo de cadastro interpreta a mensagem e volta a pedir o nome.
            is_chamar_atendente = (
                "chamar_atendente" in msg_lower
                or "chamar atendente" in msg_lower
                or "chamar um atendente" in msg_lower
                or "atendente humano" in msg_lower
                or "preciso de um humano" in msg_lower
                or "quero falar com um atendente" in msg_lower
            )
            if is_chamar_atendente:
                await self._enviar_notificacao_chamar_atendente(user_id, dados)
                try:
                    from . import database as chatbot_db
                    destrava_em = chatbot_db.get_auto_pause_until()
                    chatbot_db.set_bot_status(
                        db=self.db,
                        phone_number=user_id,
                        paused_by="cliente_chamou_atendente",
                        empresa_id=self.empresa_id,
                        desativa_chatbot_em=destrava_em,
                    )
                    print(
                        f"⏸️ Chatbot pausado para cliente {user_id} por {chatbot_db.AUTO_PAUSE_HOURS} horas "
                        f"(chamou atendente - prioridade) - chatbot_destrava_em: {destrava_em}"
                    )
                except Exception as e:
                    print(f"❌ Erro ao pausar chatbot (chamar_atendente - prioridade): {e}")
                    import traceback
                    traceback.print_exc()

                return (
                    "✅ *Solicitação enviada!*\n\n"
                    "Nossa equipe foi notificada e entrará em contato com você em breve.\n\n"
                    "Enquanto isso, posso te ajudar com alguma dúvida? 😊"
                )
            
            # Se estivermos no fluxo de cadastro de nome, prioriza esse fluxo sobre intents de produto
            if estado == STATE_CADASTRO_NOME:
                return await self._processar_cadastro_nome_rapido(user_id, mensagem, dados)

            # VERIFICA PEDIDO EM ABERTO (apenas na primeira mensagem da conversa ou se ainda não foi tratado)
            if pedido_aberto and not dados.get('pedido_aberto_tratado'):
                # Verifica se o cliente quer falar sobre o pedido ou não
                nao_quer_falar_pedido = self._detectar_nao_quer_falar_pedido(mensagem)
                
                if nao_quer_falar_pedido:
                    # Cliente não quer falar sobre o pedido - pergunta se pode cancelar
                    dados['pedido_aberto_tratado'] = True
                    dados['aguardando_confirmacao_cancelamento'] = True
                    dados['pedido_aberto_id'] = pedido_aberto.get('pedido_id')
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    numero_pedido = pedido_aberto.get('numero_pedido', 'N/A')
                    return f"Entendi! Você não quer falar sobre o pedido #{numero_pedido}.\n\n⚠️ Posso cancelar esse pedido para você? (Responda 'sim' para confirmar ou 'não' para manter o pedido)"
                
                # Cliente quer falar sobre o pedido ou não respondeu diretamente
                # Informa sobre o pedido em aberto
                dados['pedido_aberto_tratado'] = True
                dados['pedido_aberto_id'] = pedido_aberto.get('pedido_id')
                self._salvar_estado_conversa(user_id, estado, dados)
                
                numero_pedido = pedido_aberto.get('numero_pedido', 'N/A')
                status = pedido_aberto.get('status', '')
                valor_total = pedido_aberto.get('valor_total', 0.0)
                subtotal = pedido_aberto.get('subtotal', 0.0)
                taxa_entrega = pedido_aberto.get('taxa_entrega', 0.0)
                desconto = pedido_aberto.get('desconto', 0.0)
                tipo_entrega = pedido_aberto.get('tipo_entrega', '')
                created_at = pedido_aberto.get('created_at')
                itens = pedido_aberto.get('itens', [])
                endereco = pedido_aberto.get('endereco')
                meio_pagamento = pedido_aberto.get('meio_pagamento')
                mesa_codigo = pedido_aberto.get('mesa_codigo')
                
                # Mapeia status para texto legível
                status_texto = {
                    'P': 'Pendente',
                    'I': 'Em impressão',
                    'R': 'Em preparo',
                    'S': 'Saiu para entrega',
                    'A': 'Aguardando pagamento',
                    'D': 'Editado',
                    'X': 'Em edição'
                }.get(status, status)
                
                # Mapeia tipo de entrega
                tipo_entrega_texto = {
                    'DELIVERY': 'Delivery',
                    'RETIRADA': 'Retirada',
                    'BALCAO': 'Balcão',
                    'MESA': 'Mesa'
                }.get(tipo_entrega, tipo_entrega)
                
                # Formata data
                data_formatada = ""
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        data_formatada = created_at
                
                # Monta mensagem no formato compacto
                mensagem_pedido = f"📦 *Pedido #{numero_pedido}* | {status_texto} | {tipo_entrega_texto}"
                if mesa_codigo:
                    mensagem_pedido += f" | Mesa: {mesa_codigo}"
                if data_formatada:
                    mensagem_pedido += f"\n📅 {data_formatada}"
                mensagem_pedido += "\n\n*Itens:*\n"
                
                if itens:
                    for item in itens:
                        nome = item.get('nome', 'Item')
                        qtd = item.get('quantidade', 1)
                        preco_total = item.get('preco_total', 0.0)
                        mensagem_pedido += f"• {qtd}x {nome} - R$ {preco_total:.2f}\n"
                else:
                    mensagem_pedido += "Nenhum item encontrado\n"
                
                mensagem_pedido += f"\n*Resumo:* Subtotal: R$ {subtotal:.2f}"
                if taxa_entrega > 0:
                    mensagem_pedido += f" | Entrega: R$ {taxa_entrega:.2f}"
                if desconto > 0:
                    mensagem_pedido += f" | Desconto: -R$ {desconto:.2f}"
                mensagem_pedido += f"\n*TOTAL: R$ {valor_total:.2f}*"
                
                if endereco:
                    mensagem_pedido += "\n\n📍 *Entrega:*"
                    end_parts = []
                    if endereco.get('rua'):
                        end_parts.append(endereco['rua'])
                    if endereco.get('numero'):
                        end_parts.append(endereco['numero'])
                    if end_parts:
                        mensagem_pedido += f"\n{', '.join(end_parts)}"
                    endereco_line = []
                    if endereco.get('complemento'):
                        endereco_line.append(endereco['complemento'])
                    if endereco.get('bairro'):
                        endereco_line.append(endereco['bairro'])
                    if endereco_line:
                        mensagem_pedido += f"\n{', '.join(endereco_line)}"
                    cidade_line = []
                    if endereco.get('cidade'):
                        cidade_line.append(endereco['cidade'])
                    if endereco.get('cep'):
                        cidade_line.append(f"CEP: {endereco['cep']}")
                    if cidade_line:
                        mensagem_pedido += f"\n{' - '.join(cidade_line)}"
                
                if meio_pagamento:
                    mensagem_pedido += f"\n\n💳 *Pagamento:* {meio_pagamento}"
                
                mensagem_pedido += "\n\nComo posso te ajudar? 😊"
                
                # Retorna a mensagem sobre o pedido
                return mensagem_pedido

            # ========== VERIFICA SE HÁ ENDEREÇO PENDENTE DE ADIÇÃO APÓS CALCULAR TAXA ==========
            endereco_pendente = dados.get("endereco_pendente_adicao")
            if endereco_pendente:
                decisao_adicao = self._detectar_confirmacao_adicao(mensagem)
                if decisao_adicao is True:
                    # Cliente confirmou - adiciona endereço ao pedido/carrinho
                    resultado = await self._adicionar_endereco_ao_pedido(user_id, dados, endereco_pendente)
                    dados.pop("endereco_pendente_adicao", None)
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return resultado
                elif decisao_adicao is False:
                    # Cliente não quer adicionar
                    dados.pop("endereco_pendente_adicao", None)
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return "Sem problemas! Quer mais alguma coisa? 😊"

            pendentes_adicao = dados.get("pendente_adicao_itens") or []
            if pendentes_adicao:
                decisao_adicao = self._detectar_confirmacao_adicao(mensagem)
                if decisao_adicao is True:
                    itens_adicionados = []
                    carrinho_resp = None
                    for item in pendentes_adicao:
                        produto = {
                            "id": item.get("id"),
                            "tipo": item.get("tipo"),
                            "nome": item.get("nome"),
                            "preco": item.get("preco")
                        }
                        quantidade = int(item.get("quantidade", 1) or 1)
                        carrinho_resp, _ = self._adicionar_ao_carrinho(user_id, dados, produto, quantidade)
                        itens_adicionados.append(f"{quantidade}x {produto.get('nome', 'item')}")

                    dados.pop("pendente_adicao_itens", None)
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                    total_final = float(carrinho_resp.valor_total) if carrinho_resp and carrinho_resp.valor_total is not None else 0.0
                    itens_txt = ", ".join(itens_adicionados)
                    return f"✅ Adicionei {itens_txt} ao carrinho!\n\n💰 *Total agora: R$ {total_final:.2f}*\n\nMais alguma coisa? 😊"
                if decisao_adicao is False:
                    dados.pop("pendente_adicao_itens", None)
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return "Sem problemas! Quer mais alguma coisa? 😊"

            self._sincronizar_carrinho_dados(user_id, dados)

            # ========== PERGUNTAS DE PREÇO (EVITA ADICIONAR PRODUTO) ==========
            if re.search(r'(quanto\s+(que\s+)?(fica|custa|é|e)|qual\s+(o\s+)?(pre[cç]o|valor)|pre[cç]o\s+(d[aeo]|de|do)|valor\s+(d[aeo]|de|do))', msg_lower, re.IGNORECASE):
                if estado in [
                    STATE_WELCOME,
                    STATE_CONVERSANDO,
                    STATE_AGUARDANDO_PEDIDO,
                    STATE_AGUARDANDO_QUANTIDADE,
                    STATE_AGUARDANDO_MAIS_ITENS
                ]:
                    todos_produtos = self._buscar_todos_produtos()
                    itens_preco = self._extrair_itens_pergunta_preco(mensagem)
                    if len(itens_preco) > 1:
                        resposta_preco = self._gerar_resposta_preco_itens(user_id, dados, itens_preco, todos_produtos)
                        self._salvar_estado_conversa(user_id, estado, dados)
                        return resposta_preco
                    if len(itens_preco) == 1:
                        item = itens_preco[0]
                        produto = self._resolver_produto_para_preco(
                            item.get("produto_busca", ""),
                            item.get("produto_busca_alt", ""),
                            bool(item.get("prefer_alt", False)),
                            todos_produtos
                        )
                        if produto:
                            return await self._gerar_resposta_sobre_produto(user_id, produto, mensagem, dados)
                    return "Qual produto você quer saber o preço? Me fala o nome!"

            # ========== DETECÇÃO ANTECIPADA DE PAGAMENTO ==========
            # Detecta forma de pagamento APENAS se já tiver itens no pedido
            # Isso evita detectar quando cliente só está perguntando "aceitam pix?"
            pedido_contexto = dados.get('pedido_contexto', [])
            carrinho = dados.get('carrinho', [])
            tem_itens = len(pedido_contexto) > 0 or len(carrinho) > 0

            if tem_itens and not dados.get('forma_pagamento') and not dados.get('meio_pagamento_id'):
                pagamento_detectado = self._detectar_forma_pagamento_em_mensagem(mensagem)
                if pagamento_detectado:
                    dados['forma_pagamento'] = pagamento_detectado['nome']
                    dados['meio_pagamento_id'] = pagamento_detectado['id']
                    print(f"💳 Pagamento detectado antecipadamente: {pagamento_detectado['nome']} (ID: {pagamento_detectado['id']})")
                    # Salva o estado atualizado com a forma de pagamento
                    self._salvar_estado_conversa(user_id, estado, dados)

            # VERIFICA SE ESTÁ AGUARDANDO CONFIRMAÇÃO DE CANCELAMENTO DE PEDIDO
            if dados.get('aguardando_confirmacao_cancelamento'):
                pedido_id = dados.get('pedido_aberto_id')
                confirmacao = self._detectar_confirmacao_cancelamento(mensagem)
                
                if confirmacao is True:
                    # Cliente confirmou cancelamento
                    dados.pop('aguardando_confirmacao_cancelamento', None)
                    dados.pop('pedido_aberto_id', None)
                    dados.pop('pedido_aberto_tratado', None)  # Remove flag para não tentar informar novamente
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    if pedido_id:
                        sucesso, mensagem_resultado = await self._cancelar_pedido(pedido_id=pedido_id, user_id=user_id)
                        if sucesso:
                            # Limpa o carrinho temporário do schema chatbot (caso ainda exista)
                            try:
                                service = self._get_carrinho_service()
                                service.limpar_carrinho(user_id, self.empresa_id)
                            except Exception as e:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error(f"Erro ao limpar carrinho após cancelamento: {e}", exc_info=True)
                            
                            return f"✅ Pedido cancelado com sucesso!\n\n{mensagem_resultado}\n\nComo posso te ajudar agora? 😊"
                        else:
                            return f"❌ Não foi possível cancelar o pedido. {mensagem_resultado}\n\nComo posso te ajudar? 😊"
                    else:
                        # Se não tem pedido_id, tenta cancelar pelo carrinho (schema chatbot)
                        sucesso, mensagem_resultado = await self._cancelar_pedido(user_id=user_id)
                        if sucesso:
                            return f"✅ {mensagem_resultado}\n\nComo posso te ajudar agora? 😊"
                        else:
                            return f"❌ {mensagem_resultado}\n\nComo posso te ajudar? 😊"
                
                elif confirmacao is False:
                    # Cliente não quer cancelar
                    dados.pop('aguardando_confirmacao_cancelamento', None)
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return "Entendido! O pedido foi mantido. Como posso te ajudar? 😊"
                
                else:
                    # Resposta não clara, pede confirmação novamente
                    return "Não entendi 😅 Você quer cancelar o pedido? (Responda 'sim' para confirmar ou 'não' para manter o pedido)"
            
            # VERIFICA SE O CLIENTE NÃO QUER FALAR SOBRE O PEDIDO (mesmo após ter sido informado)
            if pedido_aberto and dados.get('pedido_aberto_tratado') and not dados.get('aguardando_confirmacao_cancelamento'):
                nao_quer_falar_pedido = self._detectar_nao_quer_falar_pedido(mensagem)
                
                if nao_quer_falar_pedido:
                    # Cliente não quer falar sobre o pedido - pergunta se pode cancelar
                    dados['aguardando_confirmacao_cancelamento'] = True
                    dados['pedido_aberto_id'] = pedido_aberto.get('pedido_id')
                    self._salvar_estado_conversa(user_id, estado, dados)
                    
                    numero_pedido = pedido_aberto.get('numero_pedido', 'N/A')
                    return f"Entendi! Você não quer falar sobre o pedido #{numero_pedido}.\n\n⚠️ Posso cancelar esse pedido para você? (Responda 'sim' para confirmar ou 'não' para manter o pedido)"

            # VERIFICA CARRINHO TEMPORÁRIO EM ABERTO
            carrinho_aberto = self._verificar_carrinho_aberto(user_id)
            
            # Se existe carrinho em aberto e ainda não foi tratado
            if carrinho_aberto and not dados.get('carrinho_aberto_tratado'):
                # Verifica se o cliente quer cancelar o carrinho
                confirmacao_cancelar = self._detectar_confirmacao_cancelamento_carrinho(mensagem)
                
                if confirmacao_cancelar is True:
                    # Cliente quer cancelar - pergunta confirmação
                    dados['aguardando_confirmacao_cancelamento_carrinho'] = True
                    dados['carrinho_aberto_tratado'] = True
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return "⚠️ Você quer cancelar o pedido em aberto para fazer um novo?\n\n(Responda 'sim' para confirmar ou 'não' para continuar com o pedido atual)"
                elif confirmacao_cancelar is False:
                    # Cliente quer continuar - marca como tratado e permite continuar
                    dados['carrinho_aberto_tratado'] = True
                    dados['carrinho_aberto_continuado'] = True
                    self._salvar_estado_conversa(user_id, estado, dados)
                    # Sincroniza carrinho nos dados
                    self._sincronizar_carrinho_dados(user_id, dados)
                    # Continua o processamento normalmente
                else:
                    # Primeira vez que detecta carrinho - informa sobre ele
                    dados['carrinho_aberto_tratado'] = True
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return self._formatar_mensagem_carrinho_aberto(carrinho_aberto)
            
            # Se está aguardando confirmação de cancelamento do carrinho
            if dados.get('aguardando_confirmacao_cancelamento_carrinho'):
                confirmacao = self._detectar_confirmacao_cancelamento_carrinho(mensagem)
                
                if confirmacao is True:
                    # Cliente confirmou cancelamento - remove carrinho
                    try:
                        service = self._get_carrinho_service()
                        service.limpar_carrinho(user_id, self.empresa_id)
                        dados.pop('aguardando_confirmacao_cancelamento_carrinho', None)
                        dados.pop('carrinho_aberto_tratado', None)
                        dados.pop('carrinho_aberto_continuado', None)
                        dados['carrinho'] = []
                        self._salvar_estado_conversa(user_id, estado, dados)
                        return "✅ Pedido em aberto cancelado!\n\nAgora você pode fazer um novo pedido. O que você gostaria de pedir? 😊"
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Erro ao cancelar carrinho: {e}", exc_info=True)
                        dados.pop('aguardando_confirmacao_cancelamento_carrinho', None)
                        self._salvar_estado_conversa(user_id, estado, dados)
                        return "❌ Não foi possível cancelar o pedido. Tente novamente ou continue com o pedido atual."
                elif confirmacao is False:
                    # Cliente não quer cancelar - continua com o pedido
                    dados.pop('aguardando_confirmacao_cancelamento_carrinho', None)
                    dados['carrinho_aberto_continuado'] = True
                    self._salvar_estado_conversa(user_id, estado, dados)
                    # Sincroniza carrinho nos dados
                    self._sincronizar_carrinho_dados(user_id, dados)
                    return "Perfeito! Vamos continuar com seu pedido atual. O que mais você gostaria de adicionar? 😊"
                else:
                    # Resposta não clara
                    return "Não entendi 😅 Você quer cancelar o pedido em aberto para fazer um novo? (Responda 'sim' para confirmar ou 'não' para continuar)"
            
            # Se existe carrinho em aberto e cliente tenta fazer novo pedido, bloqueia
            # Mas permite ações como ver carrinho, ver cardápio, etc
            if carrinho_aberto and dados.get('carrinho_aberto_tratado') and not dados.get('carrinho_aberto_continuado'):
                # Detecta se é tentativa de fazer novo pedido
                msg_lower = mensagem.lower().strip()
                termos_novo_pedido = [
                    'quero', 'pedir', 'pedido', 'fazer pedido', 'adicionar', 
                    'me ve', 'manda', 'vou querer', 'vou pedir', 'quero um',
                    'quero uma', 'quero dois', 'quero duas'
                ]
                
                # Verifica se a mensagem parece ser um novo pedido
                if any(termo in msg_lower for termo in termos_novo_pedido):
                    # Verifica se não é apenas uma pergunta sobre o carrinho atual ou cardápio
                    termos_ver_carrinho = ['ver', 'mostrar', 'quanto', 'total', 'resumo', 'o que tem', 'cardapio', 'cardápio', 'menu']
                    if not any(termo in msg_lower for termo in termos_ver_carrinho):
                        # É tentativa de novo pedido - pergunta sobre cancelar
                        dados['aguardando_confirmacao_cancelamento_carrinho'] = True
                        self._salvar_estado_conversa(user_id, estado, dados)
                        return self._formatar_mensagem_carrinho_aberto(carrinho_aberto)

            # VERIFICA SE ACEITA PEDIDOS PELO WHATSAPP
            config = self._get_chatbot_config()
            if config and not config.aceita_pedidos_whatsapp:
                # Detecta se a mensagem é uma tentativa de fazer pedido
                msg_lower = mensagem.lower().strip()
                termos_pedido = ['quero', 'pedir', 'pedido', 'fazer pedido', 'adicionar', 'me ve', 'manda', 'vou querer', 'vou pedir']
                if any(termo in msg_lower for termo in termos_pedido):
                    # Busca link do cardápio da empresa
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    # Retorna mensagem de redirecionamento
                    if config.mensagem_redirecionamento:
                        resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        resposta = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    return resposta

            # Se for primeira mensagem (saudação), pode retornar boas-vindas (dependendo do modo)
            if self._eh_primeira_mensagem(mensagem):
                # VERIFICA SE ACEITA PEDIDOS PELO WHATSAPP ANTES DE RESPONDER
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    # Não aceita pedidos - retorna mensagem de redirecionamento
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    # Retorna mensagem de redirecionamento
                    if config.mensagem_redirecionamento:
                        resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        resposta = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    return resposta
                
                dados['historico'] = [{"role": "user", "content": mensagem}]
                dados['carrinho'] = []
                dados['pedido_contexto'] = []  # Lista de itens mencionados na conversa
                dados['produtos_encontrados'] = self._buscar_promocoes()
                # LIMPA pagamento de conversa anterior
                dados['forma_pagamento'] = None
                dados['meio_pagamento_id'] = None
                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)

                if self.emit_welcome_message:
                    return self._gerar_mensagem_boas_vindas_conversacional()
                # Quando o WhatsApp já mandou a boas-vindas em mensagem interativa com botões,
                # não devolvemos o texto longo aqui.
                return "Perfeito! 😊 Me diga o que você gostaria de pedir."

            # ========== FLUXO DE CADASTRO RÁPIDO DE CLIENTE ==========
            
            # Estado: Coletando nome do cliente (cadastro rápido durante pedido)
            if estado == STATE_CADASTRO_NOME:
                return await self._processar_cadastro_nome_rapido(user_id, mensagem, dados)

            # ========== MODO CONVERSACIONAL (IA LIVRE) ==========
            if estado == STATE_CONVERSANDO:
                return await self._processar_conversa_ia(user_id, mensagem, dados)

            # ========== FLUXO DE ENTREGA/RETIRADA ==========

            # Estado: Perguntando se é entrega ou retirada
            if estado == STATE_PERGUNTANDO_ENTREGA_RETIRADA:
                # VERIFICA SE ACEITA PEDIDOS ANTES DE CONTINUAR FLUXO
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    # Limpa carrinho e redireciona
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        return f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                
                return await self._processar_entrega_ou_retirada(user_id, mensagem, dados)

            # ========== FLUXO DE ENDEREÇOS ==========

            # Estado: Listando endereços salvos (cliente escolhe número ou "NOVO")
            if estado == STATE_LISTANDO_ENDERECOS:
                # VERIFICA SE ACEITA PEDIDOS
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        return f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                
                return await self._processar_selecao_endereco_salvo(user_id, mensagem, dados)

            # Estado: Buscando endereço no Google Maps
            if estado == STATE_BUSCANDO_ENDERECO_GOOGLE:
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        return f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                
                return await self._processar_busca_endereco_google(user_id, mensagem, dados)

            # Estado: Selecionando endereço do Google
            if estado == STATE_SELECIONANDO_ENDERECO_GOOGLE:
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        return f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                
                return await self._processar_selecao_endereco_google(user_id, mensagem, dados)

            # Estado: Coletando complemento
            if estado == STATE_COLETANDO_COMPLEMENTO:
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        return f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                
                return await self._processar_complemento(user_id, mensagem, dados)

            # Estado: Coletando pagamento
            if estado == STATE_COLETANDO_PAGAMENTO:
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        return f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                
                return await self._processar_pagamento(user_id, mensagem, dados)

            # Estado: Confirmando pedido
            if estado == STATE_CONFIRMANDO_PEDIDO:
                # VERIFICA SE ACEITA PEDIDOS ANTES DE CONFIRMAR
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    # Não aceita pedidos - cancela o pedido e redireciona
                    dados['carrinho'] = []
                    dados.pop('carrinho_aberto_tratado', None)
                    dados.pop('carrinho_aberto_continuado', None)
                    dados.pop('aguardando_confirmacao_cancelamento_carrinho', None)
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    if config.mensagem_redirecionamento:
                        resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        resposta = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    
                    return resposta
                
                if self._detectar_confirmacao_pedido(mensagem):
                    # Salvar pedido via endpoint /checkout
                    resultado = await self._salvar_pedido_via_checkout(user_id, dados)

                    if isinstance(resultado, dict) and resultado.get('erro'):
                        # Checkout falhou - mostrar erro ao usuário
                        erro_msg = resultado.get('mensagem', 'Erro ao processar pedido')
                        return f"❌ *Ops! Não foi possível confirmar o pedido:*\n\n{erro_msg}\n\nDigite *OK* para tentar novamente ou *CANCELAR* para desistir."

                    # Sucesso - limpar carrinho e resetar estado
                    dados['carrinho'] = []
                    dados.pop('carrinho_aberto_tratado', None)
                    dados.pop('carrinho_aberto_continuado', None)
                    dados.pop('aguardando_confirmacao_cancelamento_carrinho', None)
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)

                    if resultado:
                        msg_confirmacao = "🎉 *PEDIDO CONFIRMADO!*\n"
                        msg_confirmacao += "━━━━━━━━━━━━━━━━━━━━\n\n"
                        msg_confirmacao += f"📋 *Número do pedido:* #{resultado}\n\n"
                        msg_confirmacao += "✅ Seu pedido foi enviado para a cozinha!\n"
                        msg_confirmacao += "📱 Você receberá atualizações sobre a entrega\n\n"
                        msg_confirmacao += "━━━━━━━━━━━━━━━━━━━━\n"
                        msg_confirmacao += "Obrigado pela preferência! 😊"
                        return msg_confirmacao
                    else:
                        msg_confirmacao = "🎉 *PEDIDO CONFIRMADO!*\n"
                        msg_confirmacao += "━━━━━━━━━━━━━━━━━━━━\n\n"
                        msg_confirmacao += "✅ Seu pedido foi enviado para a cozinha!\n"
                        msg_confirmacao += "📱 Você receberá atualizações sobre a entrega\n\n"
                        msg_confirmacao += "━━━━━━━━━━━━━━━━━━━━\n"
                        msg_confirmacao += "Obrigado pela preferência! 😊"
                        return msg_confirmacao
                elif 'cancelar' in mensagem.lower():
                    dados['carrinho'] = []
                    dados.pop('carrinho_aberto_tratado', None)
                    dados.pop('carrinho_aberto_continuado', None)
                    dados.pop('aguardando_confirmacao_cancelamento_carrinho', None)
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    return "✅ *Pedido cancelado!*\n\nQuando quiser fazer um pedido, é só me chamar! 😊"
                else:
                    return "❓ Não entendi 😅\n\nDigite *OK* para confirmar ou *CANCELAR* para desistir"

            # ========== VERIFICAÇÃO PRIORITÁRIA: ACEITA PEDIDOS? ==========
            # IMPORTANTE: Verifica ANTES de chamar a IA, mas apenas para TENTATIVAS CLARAS DE PEDIDO
            # NÃO bloqueia perguntas e dúvidas - o chatbot deve continuar respondendo dúvidas
            config = self._get_chatbot_config()
            if config and not config.aceita_pedidos_whatsapp:
                # Detecta se a mensagem é uma TENTATIVA CLARA de fazer pedido (não pergunta)
                msg_lower = mensagem.lower().strip()
                
                # Termos que indicam PEDIDO (ação), não pergunta
                termos_pedido_acao = [
                    'me ve', 'manda', 'coloca', 'incluir', 'anota', 'anotar',
                    'finalizar', 'fechar', 'só isso', 'pode fechar', 'levar', 'pegar',
                    'vou querer', 'vou pedir', 'fazer pedido', 'quero pedir'
                ]
                
                # Termos que indicam PERGUNTA (não bloqueia)
                termos_pergunta = [
                    'quanto', 'qual', 'o que', 'tem', 'como', 'onde', 'quando', 'por que',
                    'preço', 'custa', 'fica', 'valor', 'ingrediente', 'tamanho', 'tempo',
                    'horário', 'funcionamento', 'localização', 'endereço'
                ]
                
                # Verifica se é pergunta (não bloqueia)
                is_pergunta = any(termo in msg_lower for termo in termos_pergunta) or \
                             msg_lower.endswith('?') or \
                             'quanto custa' in msg_lower or \
                             'quanto fica' in msg_lower or \
                             'qual o preço' in msg_lower
                
                # Se for pergunta, deixa passar (não bloqueia)
                if is_pergunta:
                    print(f"✅ Permitindo pergunta (aceita_pedidos_whatsapp=False): {mensagem[:50]}")
                # Se contém termos de ação de pedido E não é pergunta, bloqueia
                elif any(termo in msg_lower for termo in termos_pedido_acao):
                    # Busca link do cardápio da empresa
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    # Retorna mensagem de redirecionamento
                    if config.mensagem_redirecionamento:
                        resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        resposta = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    
                    print(f"🚫 Bloqueado tentativa de pedido (aceita_pedidos_whatsapp=False): {mensagem[:50]}")
                    return resposta
                # Se contém "quero" ou "pedir" mas pode ser pergunta, deixa a IA decidir
                # (a IA vai interpretar corretamente como pergunta ou pedido)

            # ========== INTERPRETAÇÃO POR IA (FUNCTION CALLING) ==========
            # A IA analisa a mensagem e decide qual ação tomar

            # Busca todos os produtos disponíveis
            todos_produtos = self._buscar_todos_produtos()
            carrinho = dados.get('carrinho', [])

            # Chama a IA para interpretar a intenção do cliente
            intencao = await self._interpretar_intencao_ia(mensagem, todos_produtos, carrinho)
            funcao = intencao.get("funcao", "conversar")
            params = intencao.get("params", {})

            print(f"🎯 IA interpretou: {funcao} com params {params}")

            # ========== EXECUTA A AÇÃO BASEADA NA DECISÃO DA IA ==========

            # VERIFICA SE ACEITA PEDIDOS ANTES DE PROCESSAR AÇÕES DE PEDIDO
            # (Verificação dupla para garantir que mesmo se a IA retornar função de pedido, bloqueia)
            if config and not config.aceita_pedidos_whatsapp:
                # Se não aceita pedidos, bloqueia ações de pedido
                if funcao in ["adicionar_produto", "adicionar_produtos", "finalizar_pedido"]:
                    # Busca link do cardápio da empresa
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    # Retorna mensagem de redirecionamento
                    if config.mensagem_redirecionamento:
                        resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        resposta = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    return resposta

            # VERIFICA CARRINHO EM ABERTO ANTES DE ADICIONAR PRODUTOS
            # Se existe carrinho em aberto e cliente tenta adicionar produto, bloqueia
            if funcao in ["adicionar_produto", "adicionar_produtos", "finalizar_pedido"]:
                carrinho_aberto_check = self._verificar_carrinho_aberto(user_id)
                if carrinho_aberto_check:
                    # Se não foi tratado ainda, informa sobre ele
                    if not dados.get('carrinho_aberto_tratado'):
                        dados['carrinho_aberto_tratado'] = True
                        self._salvar_estado_conversa(user_id, estado, dados)
                        return self._formatar_mensagem_carrinho_aberto(carrinho_aberto_check)
                    # Se foi tratado mas cliente não confirmou continuar, bloqueia
                    elif dados.get('carrinho_aberto_tratado') and not dados.get('carrinho_aberto_continuado'):
                        return self._formatar_mensagem_carrinho_aberto(carrinho_aberto_check)
                    # Se cliente confirmou continuar, permite adicionar produtos normalmente

            # ADICIONAR PRODUTO
            if funcao == "adicionar_produto":
                produto_busca = params.get("produto_busca", "")
                produto_busca_alt = params.get("produto_busca_alt", "")
                prefer_alt = bool(params.get("prefer_alt", False))
                quantidade = params.get("quantidade", 1)
                personalizacao = params.get("personalizacao")  # Personalização que vem junto

                # Busca o produto pelo termo que a IA extraiu
                produto = self._resolver_produto_para_preco(
                    produto_busca, produto_busca_alt, prefer_alt, todos_produtos
                )

                if produto:
                    carrinho_resp, carrinho = self._adicionar_ao_carrinho(user_id, dados, produto, quantidade)
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                    print(f"🛒 Carrinho atual: {dados.get('carrinho', [])}")

                    # Se veio personalização junto, aplica automaticamente
                    if personalizacao:
                        acao = personalizacao.get("acao")
                        item_nome = personalizacao.get("item")
                        produto_busca_pers = produto['nome']  # Usa o produto recém-adicionado
                        
                        print(f"   🔧 Aplicando personalização automática: {acao} - {item_nome}")
                        sucesso, msg_personalizacao = self._personalizar_item_carrinho(
                            dados, acao, item_nome, produto_busca_pers
                        )
                        if sucesso:
                            self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                            print(f"   ✅ Personalização aplicada: {msg_personalizacao}")

                    carrinho = carrinho or dados.get('carrinho', [])
                    total = float(carrinho_resp.valor_total) if carrinho_resp and carrinho_resp.valor_total is not None else sum(
                        item['preco'] * item.get('quantidade', 1) for item in carrinho
                    )

                    # Monta mensagem de confirmação bonita e dinâmica
                    import random
                    msg_resposta = "✅ *Produto adicionado!*\n"
                    msg_resposta += "━━━━━━━━━━━━━━━━━━━━\n\n"
                    msg_resposta += f"*{quantidade}x {produto['nome']}*\n"
                    msg_resposta += f"R$ {produto['preco'] * quantidade:.2f}\n"
                    
                    # Adiciona mensagem de personalização se foi aplicada
                    if personalizacao:
                        acao = personalizacao.get("acao")
                        item_nome = personalizacao.get("item")
                        if acao == "remover_ingrediente":
                            msg_resposta += f"🚫 Sem: {item_nome}\n"
                        elif acao == "adicionar_extra":
                            msg_resposta += f"➕ Extra: {item_nome}\n"
                        msg_resposta += "\n"

                    # Busca ingredientes para mostrar descrição do produto (opcional - não muito longo)
                    ingredientes = self.ingredientes_service.buscar_ingredientes_por_nome_receita(produto['nome'])
                    if ingredientes and len(ingredientes) <= 3:
                        ing_lista = [i['nome'] for i in ingredientes[:3]]
                        msg_resposta += f"📋 _{', '.join(ing_lista)}_\n\n"

                    # Mostra resumo do pedido atual
                    msg_resposta += "━━━━━━━━━━━━━━━━━━━━\n"
                    msg_resposta += "🛒 *SEU PEDIDO:*\n\n"
                    for item in carrinho:
                        qtd = item.get('quantidade', 1)
                        preco_item = item['preco'] * qtd
                        msg_resposta += f"• {qtd}x {item['nome']} - R$ {preco_item:.2f}\n"
                        
                        # Mostra personalizações se houver
                        pers = item.get('personalizacoes', {})
                        if pers.get('removidos'):
                            msg_resposta += f"  🚫 Sem: {', '.join(pers['removidos'])}\n"
                        for add in pers.get('adicionais', []):
                            nome = add.get('nome', add) if isinstance(add, dict) else add
                            preco = add.get('preco', 0) if isinstance(add, dict) else 0
                            msg_resposta += f"  ➕ {nome}" + (f" (+R$ {preco:.2f})" if preco > 0 else "") + "\n"
                    
                    msg_resposta += "\n━━━━━━━━━━━━━━━━━━━━\n"
                    msg_resposta += f"💰 *TOTAL: R$ {total:.2f}*\n"
                    msg_resposta += "━━━━━━━━━━━━━━━━━━━━\n"

                    # Busca complementos disponíveis para o produto
                    complementos = self.ingredientes_service.buscar_complementos_por_nome_receita(produto['nome'])

                    if complementos:
                        tem_obrigatorio = self.ingredientes_service.tem_complementos_obrigatorios(complementos)

                        if tem_obrigatorio:
                            # Se tem complemento obrigatório, mostra e pede para escolher
                            msg_resposta += self.ingredientes_service.formatar_complementos_para_chat(complementos, produto['nome'])
                            msg_resposta += "\n\n_Escolha os complementos obrigatórios para continuar!_"
                            # Marca que está aguardando a escolha do complemento obrigatório
                            dados['aguardando_complemento'] = True
                        else:
                            # Se não for obrigatório, pergunta de forma compacta e rápida
                            # Cria lista resumida de complementos disponíveis
                            nomes_complementos = [comp.get('nome', 'Complemento') for comp in complementos]
                            if len(nomes_complementos) == 1:
                                msg_resposta += f"\n\n💬 Quer adicionar *{nomes_complementos[0]}*? (Digite o que deseja ou 'não' para continuar)"
                            elif len(nomes_complementos) <= 3:
                                complementos_txt = ", ".join([f"*{nome}*" for nome in nomes_complementos[:-1]])
                                msg_resposta += f"\n\n💬 Quer adicionar algum complemento? Temos {complementos_txt} ou *{nomes_complementos[-1]}*.\n(Digite o que deseja ou 'não' para continuar)"
                            else:
                                msg_resposta += f"\n\n💬 Quer adicionar algum complemento? Temos {len(complementos)} opções disponíveis.\n(Digite o que deseja ou 'não' para continuar)"
                            # Salva complementos para quando cliente responder
                            dados['aguardando_complemento'] = True

                        # Salva produto atual para referência dos complementos
                        dados['ultimo_produto_adicionado'] = produto['nome']
                        dados['complementos_disponiveis'] = complementos
                        self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                    else:
                        config = self._get_chatbot_config()
                        if config and not config.aceita_pedidos_whatsapp:
                            link_cardapio = self._obter_link_cardapio()
                            if config.mensagem_redirecionamento:
                                msg_final = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                            else:
                                msg_final = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                            msg_resposta += f"\n\n{msg_final}"
                        else:
                            msg_resposta += "\n\n💬 Quer adicionar mais alguma coisa ou posso fechar o pedido? 😊"

                    return msg_resposta
                else:
                    # Verifica se parece ser uma intenção genérica de pedir (não um produto específico)
                    termos_genericos = ['fazer', 'pedido', 'pedir', 'quero um', 'quero uma', 'algo', 'alguma coisa']
                    if any(t in produto_busca.lower() for t in termos_genericos):
                        return "Claro! O que você gostaria de pedir? Posso te mostrar o cardápio se quiser! 😊"
                    return f"❌ Não encontrei *{produto_busca}* no cardápio 🤔\n\nQuer que eu mostre o que temos disponível? 😊"

            # ADICIONAR MÚLTIPLOS PRODUTOS
            elif funcao == "adicionar_produtos":
                itens = params.get("itens", [])
                if not itens:
                    return "O que você gostaria de pedir?"

                mensagens_resposta = []
                carrinho_resp = None
                for item in itens:
                    produto_busca = item.get("produto_busca", "")
                    produto_busca_alt = item.get("produto_busca_alt", "")
                    prefer_alt = bool(item.get("prefer_alt", False))
                    quantidade = int(item.get("quantidade", 1) or 1)
                    produto = self._resolver_produto_para_preco(
                        produto_busca, produto_busca_alt, prefer_alt, todos_produtos
                    )
                    if not produto:
                        mensagens_resposta.append(f"❌ Não encontrei *{produto_busca}* no cardápio 😔")
                        continue

                    carrinho_resp, _ = self._adicionar_ao_carrinho(user_id, dados, produto, quantidade)
                    mensagens_resposta.append(f"✅ Adicionei {quantidade}x *{produto['nome']}* ao pedido!")

                self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                resposta_final = "\n\n".join(mensagens_resposta) if mensagens_resposta else "O que você gostaria de pedir?"
                resposta_final += "\n\nMais alguma coisa? 😊"
                return resposta_final

            # REMOVER PRODUTO
            elif funcao == "remover_produto":
                produto_busca = params.get("produto_busca", "")
                produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)

                if produto:
                    sucesso, msg_remocao, carrinho_resp, carrinho_lista = self._remover_do_carrinho(user_id, dados, produto)
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)

                    carrinho = carrinho_lista or dados.get('carrinho', [])
                    if sucesso and carrinho:
                        total = float(carrinho_resp.valor_total) if carrinho_resp and carrinho_resp.valor_total is not None else sum(
                            item['preco'] * item.get('quantidade', 1) for item in carrinho
                        )
                        msg_remocao = "✅ *Produto removido!*\n"
                        msg_remocao += "━━━━━━━━━━━━━━━━━━━━\n\n"
                        msg_remocao += f"💰 *Total agora: R$ {total:.2f}*\n\n"
                        msg_remocao += "💬 Quer adicionar mais alguma coisa? 😊"
                        return msg_remocao
                    if sucesso:
                        return "✅ *Produto removido!*\n\n🛒 Seu carrinho está vazio agora.\n\nO que você gostaria de pedir? 😊"
                    return msg_remocao
                else:
                    return f"❌ Não encontrei *{produto_busca}* no seu pedido 🤔\n\nQuer ver o que tem no carrinho?"

            # FINALIZAR PEDIDO
            elif funcao == "finalizar_pedido":
                if carrinho:
                    # Sempre pergunta entrega/retirada, mesmo se já tiver definido antes
                    # Isso garante que o cliente escolha novamente para cada pedido
                    tipo_entrega_anterior = dados.get('tipo_entrega')
                    if tipo_entrega_anterior:
                        # Limpa tipo_entrega anterior para garantir nova escolha
                        dados['tipo_entrega'] = None
                        dados['endereco_texto'] = None
                        dados['endereco_id'] = None
                    print("🛒 Cliente quer finalizar, perguntando entrega ou retirada")
                    return self._perguntar_entrega_ou_retirada(user_id, dados)
                else:
                    return "🛒 *Seu carrinho está vazio!*\n\nO que você gostaria de pedir hoje? 😊"

            # VER CARDÁPIO
            elif funcao == "ver_cardapio":
                print("📋 Cliente pediu para ver o cardápio")
                # VERIFICA SE ACEITA PEDIDOS PELO WHATSAPP
                config = self._get_chatbot_config()
                if config and not config.aceita_pedidos_whatsapp:
                    # Não aceita pedidos - retorna link do cardápio em vez de listar produtos
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
                        empresa = result.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar link do cardápio: {e}")
                        link_cardapio = LINK_CARDAPIO
                    
                    # Retorna mensagem com link do cardápio
                    if config.mensagem_redirecionamento:
                        resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                    else:
                        resposta = f"📲 Para ver nosso cardápio completo e fazer seu pedido, acesse pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    return resposta
                
                # Se aceita pedidos, mostra a lista normalmente
                return self._gerar_lista_produtos(todos_produtos, carrinho)

            # VER CARRINHO
            elif funcao == "ver_carrinho":
                print("🛒 Cliente pediu para ver o carrinho")
                if carrinho:
                    msg = self._formatar_carrinho(carrinho)
                    config = self._get_chatbot_config()
                    if config and not config.aceita_pedidos_whatsapp:
                        link_cardapio = self._obter_link_cardapio()
                        if config.mensagem_redirecionamento:
                            msg_final = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                        else:
                            msg_final = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                        msg += f"\n\n{msg_final}"
                    else:
                        msg += "\n\n💬 Quer adicionar mais alguma coisa ou posso fechar o pedido? 😊"
                    return msg
                else:
                    return "🛒 *Seu carrinho está vazio!*\n\nO que você gostaria de pedir hoje? 😊"

            # INFORMAR SOBRE PRODUTO
            elif funcao == "informar_sobre_produto":
                produto_busca = params.get("produto_busca", "")
                pergunta = params.get("pergunta", "")
                produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)

                if produto:
                    # Gera resposta contextual sobre o produto com ingredientes reais
                    return await self._gerar_resposta_sobre_produto(user_id, produto, pergunta, dados)
                else:
                    sugestoes = self._buscar_contexto_catalogo_rag(produto_busca or pergunta or mensagem, limit=6)
                    if sugestoes:
                        return (
                            "Não achei esse produto com esse nome. Você quis dizer algum desses?\n\n"
                            f"{sugestoes}\n\n"
                            "Me diga o nome exato que eu te explico. 😊"
                        )
                    return "Qual produto você quer saber mais? Me fala o nome!"
            elif funcao == "informar_sobre_produtos":
                itens = params.get("itens", [])
                if itens:
                    resposta_preco = self._gerar_resposta_preco_itens(user_id, dados, itens, todos_produtos)
                    self._salvar_estado_conversa(user_id, estado, dados)
                    return resposta_preco
                return "Qual produto você quer saber o preço?"

            # CALCULAR TAXA DE ENTREGA
            elif funcao == "calcular_taxa_entrega":
                # Extrai endereço usando IA
                mensagem_original = params.get("mensagem_original", "")
                endereco = params.get("endereco", "")
                
                # Se não veio endereço direto, extrai da mensagem original com IA
                if not endereco and mensagem_original:
                    endereco = await self._extrair_endereco_com_ia(mensagem_original)
                
                return await self._calcular_e_responder_taxa_entrega(user_id, endereco, dados)

            # CHAMAR ATENDENTE
            elif funcao == "chamar_atendente":
                # Cliente quer chamar atendente humano
                # Envia notificação para a empresa
                await self._enviar_notificacao_chamar_atendente(user_id, dados)
                
                # PAUSA O CHATBOT PARA ESTE CLIENTE (por conta própria - 3 horas)
                try:
                    from . import database as chatbot_db
                    destrava_em = chatbot_db.get_auto_pause_until()
                    chatbot_db.set_bot_status(
                        db=self.db,
                        phone_number=user_id,
                        paused_by="cliente_chamou_atendente",
                        empresa_id=self.empresa_id,
                        desativa_chatbot_em=destrava_em,
                    )
                    print(f"⏸️ Chatbot pausado para cliente {user_id} por {chatbot_db.AUTO_PAUSE_HOURS} horas (chamou atendente via IA) - chatbot_destrava_em: {destrava_em}")
                except Exception as e:
                    print(f"❌ Erro ao pausar chatbot: {e}")
                    import traceback
                    traceback.print_exc()
                
                return "✅ *Solicitação enviada!*\n\nNossa equipe foi notificada e entrará em contato com você em breve.\n\nEnquanto isso, posso te ajudar com alguma dúvida? 😊"

            # INICIAR NOVO PEDIDO
            elif funcao == "iniciar_novo_pedido":
                # Verifica se há carrinho em aberto
                carrinho_aberto = self._verificar_carrinho_aberto(user_id)
                
                if carrinho_aberto:
                    # Há carrinho aberto - pergunta confirmação antes de limpar
                    dados['aguardando_confirmacao_cancelamento_carrinho'] = True
                    dados['carrinho_aberto_tratado'] = True
                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    return self._formatar_mensagem_carrinho_aberto(carrinho_aberto)
                else:
                    # Não há carrinho aberto - apenas reinicia o contexto
                    dados['pedido_contexto'] = []
                    dados['ultimo_produto_adicionado'] = None
                    dados['ultimo_produto_mencionado'] = None
                    dados.pop('pedido_aberto_id', None)
                    dados.pop('pedido_aberto_tratado', None)
                    self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                    return "✅ Perfeito! Vamos começar um novo pedido! 😊\n\nO que você gostaria de pedir hoje?"

            # INFORMAR SOBRE ESTABELECIMENTO
            elif funcao == "informar_sobre_estabelecimento":
                tipo_pergunta = params.get("tipo_pergunta", "ambos")
                empresas = self._buscar_empresas_ativas()
                
                if not empresas:
                    return "❌ Não foi possível obter informações do estabelecimento no momento. 😔"
                
                # Busca empresa atual (se não estiver na lista, busca do banco)
                empresa_atual = None
                for emp in empresas:
                    if emp['id'] == self.empresa_id:
                        empresa_atual = emp
                        break
                
                # Se não encontrou na lista, busca diretamente do banco
                if not empresa_atual:
                    try:
                        result = self.db.execute(text("""
                            SELECT id, nome, bairro, cidade, estado, logradouro, numero, 
                                   complemento, horarios_funcionamento
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """), {"empresa_id": self.empresa_id})
                        row = result.fetchone()
                        if row:
                            empresa_atual = {
                                'id': row[0],
                                'nome': row[1],
                                'bairro': row[2],
                                'cidade': row[3],
                                'estado': row[4],
                                'logradouro': row[5],
                                'numero': row[6],
                                'complemento': row[7],
                                'horarios_funcionamento': row[8]
                            }
                            # Adiciona à lista para usar na formatação
                            empresas.append(empresa_atual)
                    except Exception as e:
                        print(f"❌ Erro ao buscar empresa atual: {e}")
                
                resposta = ""
                
                if tipo_pergunta in ["horario", "ambos"]:
                    if empresa_atual:
                        horarios = self._formatar_horarios_funcionamento(empresa_atual.get('horarios_funcionamento'))
                        resposta += horarios + "\n\n"
                    else:
                        resposta += "Horários de funcionamento não disponíveis.\n\n"
                
                if tipo_pergunta in ["localizacao", "ambos"]:
                    localizacao = self._formatar_localizacao_empresas(empresas, self.empresa_id)
                    resposta += localizacao
                
                self._salvar_estado_conversa(user_id, estado, dados)
                return resposta.strip()

            # PERSONALIZAR PRODUTO (remover ingrediente ou adicionar extra)
            elif funcao == "personalizar_produto":
                acao = params.get("acao", "")
                item_nome = params.get("item", "")
                produto_busca = params.get("produto_busca", "")

                print(f"🔧 Personalizando: acao={acao}, item={item_nome}, produto={produto_busca}")

                if not acao or not item_nome:
                    return "Não entendi a personalização 😅 Tenta de novo!"

                sucesso, mensagem_resposta = self._personalizar_item_carrinho(
                    dados, acao, item_nome, produto_busca
                )
                self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)

                if sucesso:
                    mensagem_resposta += "\n\nMais alguma coisa? 😊"
                return mensagem_resposta

            # VER ADICIONAIS/COMPLEMENTOS DISPONÍVEIS
            elif funcao == "ver_adicionais":
                produto_busca = params.get("produto_busca", "")

                # Se não especificou produto, usa o último adicionado ou último do carrinho
                if not produto_busca:
                    produto_busca = dados.get('ultimo_produto_adicionado', '')
                if not produto_busca and carrinho:
                    produto_busca = carrinho[-1]['nome']

                if produto_busca:
                    # Primeiro tenta buscar complementos (estrutura correta)
                    complementos = self.ingredientes_service.buscar_complementos_por_nome_receita(produto_busca)

                    if complementos:
                        msg = self.ingredientes_service.formatar_complementos_para_chat(complementos, produto_busca)
                        msg += "\n\nPara adicionar, diga o nome do item (ex: *Bacon Extra*) 😊"
                        return msg

                    # Se não tem complementos, busca adicionais diretos
                    adicionais = self.ingredientes_service.buscar_adicionais_por_nome_receita(produto_busca)
                    if adicionais:
                        msg = f"➕ *Adicionais para {produto_busca}:*\n\n"
                        for add in adicionais:
                            msg += f"• {add['nome']} - +R$ {add['preco']:.2f}\n"
                        msg += "\nPara adicionar, diga o nome do item 😊"
                        return msg

                # Se não encontrou específicos, mostra todos
                todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
                if todos_adicionais:
                    msg = "➕ *Adicionais disponíveis:*\n\n"
                    for add in todos_adicionais:
                        msg += f"• {add['nome']} - +R$ {add['preco']:.2f}\n"
                    msg += "\nPara adicionar, diga o nome do item 😊"
                    return msg
                else:
                    return "No momento não temos adicionais extras disponíveis 😅"

            # VER COMBOS DISPONÍVEIS
            elif funcao == "ver_combos":
                print("🎁 Cliente pediu para ver os combos")
                return self.ingredientes_service.formatar_combos_para_chat()

            # CONVERSAR (função principal para interação natural)
            elif funcao == "conversar":
                tipo_conversa = params.get("tipo_conversa", "resposta_generica")
                contexto = params.get("contexto", "")

                print(f"💬 Conversa tipo: {tipo_conversa}")

                # Gera resposta conversacional natural
                return await self._gerar_resposta_conversacional(
                    user_id, mensagem, tipo_conversa, contexto, todos_produtos, carrinho, dados
                )

            # Fallback - trata como conversa
            else:
                return await self._gerar_resposta_conversacional(
                    user_id, mensagem, "resposta_generica", "", todos_produtos, carrinho, dados
                )

        except httpx.TimeoutException:
            print("⏰ Timeout no Groq - usando fallback")
            return await self._fallback_resposta_inteligente(mensagem, dados, user_id)

        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            import traceback
            traceback.print_exc()
            # Fallback inteligente - nunca retorna erro
            return await self._fallback_resposta_inteligente(mensagem, dados, user_id)


# Função principal para usar no webhook
async def processar_mensagem_groq(
    db: Session,
    user_id: str,
    mensagem: str,
    empresa_id: int = 1,
    emit_welcome_message: bool = True,
    prompt_key: str = DEFAULT_PROMPT_KEY,
    pedido_aberto: Optional[Dict[str, Any]] = None
) -> str:
    """
    Processa mensagem usando Groq API com LLaMA 3.1
    Também salva as mensagens no banco para exibição no Preview WhatsApp
    """
    from . import database as chatbot_db
    from datetime import datetime

    # 1. Busca ou cria conversa no banco chatbot.conversations
    conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id)

    if conversations:
        conversation_id = conversations[0]['id']
    else:
        # Cria nova conversa
        conversation_id = chatbot_db.create_conversation(
            db=db,
            session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=user_id,
            prompt_key=prompt_key,
            model="groq-sales",
            empresa_id=empresa_id
        )
        print(f"   ✅ Nova conversa criada no banco: {conversation_id}")

    # 2. Salva mensagem do usuário no banco (se ainda não foi salva)
    # Verifica se a mensagem já foi salva recentemente (evita duplicatas)
    from sqlalchemy import text
    try:
        check_recent = text("""
            SELECT id FROM chatbot.messages
            WHERE conversation_id = :conversation_id
            AND role = 'user'
            AND content = :content
            AND created_at > NOW() - INTERVAL '5 seconds'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        result = db.execute(check_recent, {
            "conversation_id": conversation_id,
            "content": mensagem
        })
        existing = result.fetchone()
        if existing:
            user_message_id = existing[0]
            print(f"   ℹ️ Mensagem do usuário já estava salva (ID: {user_message_id})")
        else:
            user_message_id = chatbot_db.create_message(db, conversation_id, "user", mensagem)
    except Exception as e:
        # Em caso de erro, tenta salvar normalmente
        print(f"   ⚠️ Erro ao verificar mensagem existente: {e}")
        user_message_id = chatbot_db.create_message(db, conversation_id, "user", mensagem)
    
    # 2.1. Envia notificação WebSocket de nova mensagem do usuário
    try:
        from .notifications import send_chatbot_websocket_notification
        await send_chatbot_websocket_notification(
            empresa_id=empresa_id,
            notification_type="nova_mensagem",
            title="Nova Mensagem Recebida",
            message=f"Nova mensagem de {user_id}",
            data={
                "conversation_id": conversation_id,
                "message_id": user_message_id,
                "user_id": user_id,
                "role": "user",
                "content_preview": mensagem[:100] if len(mensagem) > 100 else mensagem
            }
        )
    except Exception as e:
        # Não falha se WebSocket falhar
        print(f"   ⚠️ Erro ao enviar notificação WebSocket (user): {e}")

    # 3. Processa mensagem com o handler
    handler = GroqSalesHandler(db, empresa_id, emit_welcome_message=emit_welcome_message, prompt_key=prompt_key)
    resposta = await handler.processar_mensagem(user_id, mensagem, pedido_aberto=pedido_aberto)

    # 4. Salva resposta do bot no banco
    # Se a resposta confirmou um pedido, tentamos extrair o pedido_id e gravar em metadata
    # para permitir rastrear o telefone (user_id) associado ao pedido depois.
    extra_metadata = None
    try:
        import re

        # Ex.: "📋 *Número do pedido:* #123" (formatação do fluxo de checkout)
        m = re.search(r"n[úu]mero do pedido:\s*#\s*(\d+)", str(resposta), flags=re.IGNORECASE)
        if m:
            extra_metadata = {"pedido_id": int(m.group(1)), "empresa_id": int(empresa_id)}
    except Exception:
        extra_metadata = None

    try:
        from app.api.chatbot.adapters.message_persistence_adapter import ChatMessagePersistenceAdapter
        from app.api.chatbot.contracts.message_persistence_contract import (
            ChatMessageSenderType,
            ChatMessageSourceType,
            PersistChatMessageCommand,
        )

        persistence = ChatMessagePersistenceAdapter(db)
        assistant_message_id = persistence.persist_message(
            PersistChatMessageCommand(
                conversation_id=conversation_id,
                role="assistant",
                content=str(resposta),
                empresa_id=int(empresa_id) if empresa_id is not None else None,
                whatsapp_message_id=None,  # será vinculado depois no router quando enviar pelo WhatsApp
                source_type=ChatMessageSourceType.IA,
                sender_type=ChatMessageSenderType.AI,
                metadata=extra_metadata,
            )
        )
    except Exception:
        # fallback compatível
        assistant_message_id = chatbot_db.create_message(
            db,
            conversation_id,
            "assistant",
            resposta,
            extra_metadata=extra_metadata,
        )
    
    # 4.1. Envia notificação WebSocket de resposta do bot
    try:
        from .notifications import send_chatbot_websocket_notification
        await send_chatbot_websocket_notification(
            empresa_id=empresa_id,
            notification_type="chatbot_message",
            title="Nova Resposta do Bot",
            message=f"Bot respondeu na conversa {conversation_id}",
            data={
                "conversation_id": conversation_id,
                "message_id": assistant_message_id,
                "user_id": user_id,
                "role": "assistant",
                "content_preview": resposta[:100] if len(resposta) > 100 else resposta
            }
        )
    except Exception as e:
        # Não falha se WebSocket falhar
        print(f"   ⚠️ Erro ao enviar notificação WebSocket (assistant): {e}")

    return resposta

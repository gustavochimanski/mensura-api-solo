"""
Handler de vendas integrado com Groq API (LLaMA 3.1 rápido e gratuito)
Inclui fluxo de endereços com Google Maps e endereços salvos
"""
import os
import httpx
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from datetime import datetime

from .sales_prompts import SALES_SYSTEM_PROMPT
from .address_service import ChatbotAddressService
from .ingredientes_service import (
    IngredientesService,
    detectar_remocao_ingrediente,
    detectar_adicao_extra,
    detectar_pergunta_ingredientes
)

# Configuração do Groq - API Key deve ser configurada via variável de ambiente
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"  # Modelo rápido do Groq

# Link do cardápio (configurável)
LINK_CARDAPIO = "https://chatbot.mensuraapi.com.br"

# Definição das funções que a IA pode chamar (Function Calling)
AI_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "adicionar_produto",
            "description": "Adiciona um produto ao carrinho. Use APENAS quando o cliente CLARAMENTE quer pedir algo específico. Exemplos: 'me ve uma coca', 'quero 2 pizzas', 'manda um x-bacon', 'uma coca cola'",
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
            "description": "Cliente quer SABER MAIS sobre um produto específico. Exemplos: 'o que vem no x-bacon?', 'qual o tamanho da pizza?', 'tem lactose?', 'é picante?', 'o que tem na calabresa?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_busca": {
                        "type": "string",
                        "description": "Nome do produto que o cliente quer saber mais"
                    },
                    "pergunta": {
                        "type": "string",
                        "description": "O que o cliente quer saber (ingredientes, tamanho, etc)"
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
            "description": "Cliente quer PERSONALIZAR um produto removendo ingrediente ou adicionando extra. Exemplos: 'sem cebola', 'tira o tomate', 'com queijo extra', 'adiciona bacon', 'pizza sem azeitona'",
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

❌ NÃO use adicionar_produto para:
   - "o que tem?" → use conversar
   - "tem coca?" → use conversar (é pergunta, não pedido)
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

✅ personalizar_produto - Quando quer CUSTOMIZAR um produto (tirar ingrediente ou adicionar extra):
   - "sem cebola" → personalizar_produto(acao="remover_ingrediente", item="cebola")
   - "tira o tomate" → personalizar_produto(acao="remover_ingrediente", item="tomate")
   - "com queijo extra" → personalizar_produto(acao="adicionar_extra", item="queijo extra")
   - "adiciona bacon" → personalizar_produto(acao="adicionar_extra", item="bacon")
   - "pizza sem azeitona" → personalizar_produto(produto_busca="pizza", acao="remover_ingrediente", item="azeitona")
   - "borda recheada" → personalizar_produto(acao="adicionar_extra", item="borda recheada")

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


class GroqSalesHandler:
    """
    Handler de vendas usando Groq API com LLaMA 3.1
    Busca dados do banco e gera respostas naturais
    Integra fluxo de endereços com Google Maps
    """

    def __init__(self, db: Session, empresa_id: int = 1):
        self.db = db
        self.empresa_id = empresa_id
        self.address_service = ChatbotAddressService(db, empresa_id)
        self.ingredientes_service = IngredientesService(db, empresa_id)

    def _interpretar_intencao_regras(self, mensagem: str, produtos: List[Dict], carrinho: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Interpretação de intenção usando regras simples (fallback quando Groq não disponível)
        Retorna None se não conseguir interpretar, ou dict com funcao e params
        """
        import re
        msg = mensagem.lower().strip()

        # Saudações
        if re.match(r'^(oi|ola|olá|eae|e ai|eaí|bom dia|boa tarde|boa noite|hey|hi)[\s!?]*$', msg):
            return {"funcao": "conversar", "params": {"tipo_conversa": "saudacao"}}

        # Ver cardápio - perguntas sobre o que tem, quais produtos, etc.
        if re.search(r'(cardapio|cardápio|menu|lista|catalogo|catálogo)', msg):
            return {"funcao": "ver_cardapio", "params": {}}

        # Perguntas sobre o que tem disponível (DEVE vir ANTES de adicionar produto)
        if re.search(r'(o\s*que\s*(mais\s*)?(tem|vende|vocês? tem|vcs tem)|quais?\s*(que\s*)?(tem|produto|opç[oõ]es)|mostra\s*(ai|aí|os\s*produto)|que\s*produto|tem\s*o\s*que)', msg):
            return {"funcao": "ver_cardapio", "params": {}}

        # Ver combos
        if re.search(r'(combo|combos|promoção|promocao|promoções|promocoes)', msg):
            return {"funcao": "ver_combos", "params": {}}

        # Ver carrinho
        if re.search(r'(quanto\s*(ta|tá|está)|meu\s*pedido|carrinho|o\s*que\s*(eu\s*)?pedi)', msg):
            return {"funcao": "ver_carrinho", "params": {}}

        # Finalizar pedido (explícito)
        if re.search(r'(finalizar|fechar|so\s*isso|só\s*isso|pronto|é\s*isso|acabou|era\s*isso|só$|so$)', msg):
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
                return {"funcao": "conversar", "params": {"tipo_conversa": "nao_entendi"}}

        # Remover produto
        if re.search(r'(tira|remove|cancela|retira)\s+(?:a|o)?\s*(.+)', msg):
            match = re.search(r'(tira|remove|cancela|retira)\s+(?:a|o)?\s*(.+)', msg)
            if match:
                return {"funcao": "remover_produto", "params": {"produto_busca": match.group(2).strip()}}

        # Personalização (sem/tira ingrediente)
        if re.search(r'sem\s+(\w+)', msg):
            match = re.search(r'sem\s+(\w+)', msg)
            if match:
                return {"funcao": "personalizar_produto", "params": {"acao": "remover_ingrediente", "item": match.group(1)}}

        # Adicional extra
        if re.search(r'(mais|extra|adiciona)\s+(\w+)', msg):
            match = re.search(r'(mais|extra|adiciona)\s+(\w+)', msg)
            if match:
                return {"funcao": "personalizar_produto", "params": {"acao": "adicionar_extra", "item": match.group(2)}}

        # Ver adicionais
        if re.search(r'(adicionais|extras|o\s*que\s*posso\s*adicionar)', msg):
            return {"funcao": "ver_adicionais", "params": {}}

        # Informação sobre produto (o que tem, o q tem, ingredientes, etc.)
        if re.search(r'(o\s*q(ue)?\s*(vem|tem|ve|é)\s*(n[oa]|d[oa])?|qu?al.*(ingrediente|composi[çc][aã]o)|ingredientes?\s*(d[oa])|composi[çc][aã]o)', msg):
            match = re.search(r'(n[oa]|d[oa]|da|do)\s+(.+?)(\?|$)', msg)
            if match:
                return {"funcao": "informar_sobre_produto", "params": {"produto_busca": match.group(2).strip()}}
            # Tenta extrair produto de outra forma
            match2 = re.search(r'(pizza|x-\w+|coca|guarana|agua|cerveja|batata|onion)[\w\s]*', msg)
            if match2:
                return {"funcao": "informar_sobre_produto", "params": {"produto_busca": match2.group(0).strip()}}

        # Adicionar produto (padrões: "quero X", "me ve X", "manda X", "X por favor")
        patterns_pedido = [
            r'(?:quero|qro)\s+(?:uma?|duas?|dois|\d+)?\s*(.+)',
            r'(?:me\s+)?(?:ve|vê|manda|traz)\s+(?:uma?|duas?|dois|\d+)?\s*(.+)',
            r'(?:uma?|duas?|dois|\d+)\s+(.+?)(?:\s+por\s+favor)?$',
            r'(?:pode\s+ser|vou\s+querer)\s+(?:uma?|duas?|dois|\d+)?\s*(.+)',
        ]

        for pattern in patterns_pedido:
            match = re.search(pattern, msg)
            if match:
                produto = match.group(1).strip()
                # Extrai quantidade se houver
                qtd_match = re.search(r'^(\d+)\s*x?\s*', produto)
                quantidade = int(qtd_match.group(1)) if qtd_match else 1
                if qtd_match:
                    produto = produto[qtd_match.end():].strip()
                return {"funcao": "adicionar_produto", "params": {"produto_busca": produto, "quantidade": quantidade}}

        # ÚLTIMO RECURSO: Verifica se a mensagem é um nome de produto direto
        # Isso captura casos como "coca", "pizza calabresa"
        if len(msg) >= 2 and len(msg) <= 50:
            # Verifica se não é uma pergunta ou frase comum
            palavras_ignorar = [
                'sim', 'ok', 'obrigado', 'obrigada', 'valeu', 'blz', 'beleza', 'certo', 'ta', 'tá',
                'nao', 'não', 'qual', 'quais', 'que', 'como', 'onde', 'quando', 'porque', 'por que'
            ]
            # Verifica se não é uma pergunta (termina com ?)
            if msg.endswith('?'):
                return None
            # Verifica se não contém palavras interrogativas
            if any(p in msg for p in palavras_ignorar):
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
        # PRIMEIRO: Tenta interpretação por regras (mais rápido e não precisa de API)
        resultado_regras = self._interpretar_intencao_regras(mensagem, produtos, carrinho)
        if resultado_regras:
            print(f"🎯 Regras interpretaram: {resultado_regras['funcao']}({resultado_regras['params']})")
            return resultado_regras

        # SE GROQ_API_KEY não estiver configurado, usa fallback
        if not GROQ_API_KEY:
            print(f"⚠️ GROQ_API_KEY não configurado, usando fallback")
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

                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }

                print(f"🧠 IA interpretando: '{mensagem}'")
                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

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
                        return {"funcao": funcao, "params": params}

                    # Se não tem tool_calls, trata como conversa
                    content = message.get("content", "")
                    print(f"⚠️ IA não chamou função, tratando como conversa")
                    return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica", "contexto": content}}

                else:
                    print(f"❌ Erro na API Groq: {response.status_code}")
                    # Ainda assim tenta conversar
                    return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}

        except Exception as e:
            print(f"❌ Erro ao interpretar intenção: {e}")
            return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}

    def _buscar_produto_por_termo(self, termo: str, produtos: List[Dict]) -> Optional[Dict]:
        """
        Busca um produto na lista usando o termo fornecido pela IA.
        Usa busca fuzzy para encontrar o melhor match.
        """
        termo_lower = termo.lower().strip()

        # Remove acentos
        def remover_acentos(texto):
            acentos = {'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
                       'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u', 'ç': 'c'}
            for acentuado, sem_acento in acentos.items():
                texto = texto.replace(acentuado, sem_acento)
            return texto

        termo_sem_acento = remover_acentos(termo_lower)

        # 1. Match exato no nome
        for produto in produtos:
            nome_lower = produto['nome'].lower()
            nome_sem_acento = remover_acentos(nome_lower)
            if termo_lower == nome_lower or termo_sem_acento == nome_sem_acento:
                print(f"✅ Match exato: {produto['nome']}")
                return produto

        # 2. Nome contém o termo
        for produto in produtos:
            nome_lower = produto['nome'].lower()
            nome_sem_acento = remover_acentos(nome_lower)
            if termo_sem_acento in nome_sem_acento or termo_lower in nome_lower:
                print(f"✅ Match parcial (termo no nome): {produto['nome']}")
                return produto

        # 3. Termo contém o nome do produto
        for produto in produtos:
            nome_lower = produto['nome'].lower()
            nome_sem_acento = remover_acentos(nome_lower)
            # Busca cada palavra do nome no termo
            palavras_nome = nome_sem_acento.split()
            for palavra in palavras_nome:
                if len(palavra) > 3 and palavra in termo_sem_acento:
                    print(f"✅ Match por palavra '{palavra}': {produto['nome']}")
                    return produto

        # 4. Match por palavras-chave comuns
        mapeamento = {
            'coca': ['coca-cola', 'coca cola', 'cocacola'],
            'pepsi': ['pepsi'],
            'guarana': ['guarana', 'guaraná'],
            'pizza': ['pizza'],
            'hamburguer': ['hamburguer', 'hamburger', 'burger', 'burguer'],
            'x-': ['x-bacon', 'x-tudo', 'x-salada', 'x-burguer'],
            'batata': ['batata', 'fritas'],
            'calabresa': ['calabresa'],
            'frango': ['frango'],
            'bacon': ['bacon'],
        }

        for chave, variantes in mapeamento.items():
            if chave in termo_sem_acento or any(v in termo_sem_acento for v in variantes):
                for produto in produtos:
                    nome_sem_acento = remover_acentos(produto['nome'].lower())
                    if chave in nome_sem_acento or any(v in nome_sem_acento for v in variantes):
                        print(f"✅ Match por mapeamento '{chave}': {produto['nome']}")
                        return produto

        print(f"❌ Produto não encontrado para termo: {termo}")
        return None

    def _gerar_mensagem_boas_vindas(self) -> str:
        """
        Gera mensagem de boas-vindas CURTA e NATURAL
        """
        import random

        # Busca alguns produtos para sugestão
        produtos = self._buscar_promocoes()

        # Mensagens variadas de boas-vindas
        saudacoes = [
            "E aí! 😊 Tudo bem?",
            "Opa! Beleza?",
            "Olá! Tudo certo?",
            "E aí, tudo bem? 👋",
        ]

        saudacao = random.choice(saudacoes)

        mensagem = f"{saudacao}\n\n"
        mensagem += "Aqui é o atendimento do delivery!\n\n"

        # Mostra apenas 2-3 sugestões rápidas
        if produtos:
            destaques = produtos[:3]
            mensagem += "🔥 *Hoje tá saindo muito:*\n"
            for p in destaques:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        mensagem += "O que vai ser hoje? 😋"

        return mensagem

    def _gerar_mensagem_boas_vindas_conversacional(self) -> str:
        """Gera mensagem de boas-vindas para modo conversacional"""
        produtos = self._buscar_promocoes()

        mensagem = "Olá! 😊 Bem-vindo ao nosso delivery!\n\n"
        mensagem += "Estou aqui para te ajudar a fazer seu pedido.\n\n"

        if produtos:
            destaques = produtos[:3]
            mensagem += "🔥 *Destaques de hoje:*\n"
            for p in destaques:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        mensagem += "Me conta o que você gostaria! Pode perguntar sobre qualquer produto, ver o cardápio, tirar dúvidas... Estou à disposição! 😊"

        return mensagem

    async def _processar_conversa_ia(self, user_id: str, mensagem: str, dados: dict) -> str:
        """
        Processa mensagem no modo conversacional usando IA livre.
        A IA conversa naturalmente, tira dúvidas e anota o pedido.
        """
        import json
        import re

        # Atualiza histórico
        historico = dados.get('historico', [])
        historico.append({"role": "user", "content": mensagem})

        # Busca dados do cardápio
        todos_produtos = self._buscar_todos_produtos()
        pedido_contexto = dados.get('pedido_contexto', [])

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

        # Prompt do sistema para IA conversacional
        system_prompt = f"""Você é um atendente de delivery simpático e prestativo. Seu nome é Assistente Virtual.

SUAS RESPONSABILIDADES:
1. Conversar naturalmente com o cliente
2. Tirar dúvidas sobre produtos (ingredientes, preços, tamanhos)
3. Anotar os pedidos do cliente mentalmente
4. Quando o cliente quiser finalizar, perguntar se pode prosseguir para entrega

CARDÁPIO COMPLETO:
{cardapio_texto}

{pedido_atual}

REGRAS IMPORTANTES:
- Seja DIRETO e objetivo. NÃO peça confirmação do pedido, apenas anote e pergunte se quer mais algo
- Quando o cliente PEDIR produtos, ANOTE IMEDIATAMENTE e diga "Anotado! [itens]. Quer mais algo?"
- NÃO pergunte "certo?", "é isso?", "confirma?" - apenas anote e siga em frente
- Quando o cliente PERGUNTAR sobre um produto (ingredientes, preço), responda a dúvida SEM adicionar ao pedido
- Se o cliente quiser personalizar (sem cebola, com bacon extra), anote a personalização
- Quando o cliente disser "só isso", "não quero mais nada", "pode fechar", use acao "prosseguir_entrega"
- NÃO invente produtos ou preços, use apenas o que está no cardápio
- Respostas CURTAS (máximo 2-3 linhas)

EXEMPLOS DE COMPORTAMENTO CORRETO:
- Cliente: "quero 1 pizza calabresa e 1 coca" → "Anotado! 1 Pizza Calabresa e 1 Coca-Cola. Quer mais algo? 😊" (acao: adicionar)
- Cliente: "o que tem na pizza?" → [responde ingredientes] (acao: nenhuma)
- Cliente: "só isso" → "Perfeito! Podemos prosseguir para a entrega? 🚗" (acao: prosseguir_entrega)
- Cliente: "sim" (após perguntar se quer finalizar) → use acao "prosseguir_entrega"

FORMATO DE RESPOSTA - SEMPRE RETORNE JSON VÁLIDO, SEM EXCEÇÃO:
{{
    "resposta": "sua mensagem curta para o cliente",
    "acao": "nenhuma" | "adicionar" | "remover" | "prosseguir_entrega",
    "itens": [
        {{
            "nome": "nome exato do produto do cardápio",
            "quantidade": 1,
            "removidos": [],
            "adicionais": []
        }}
    ]
}}

REGRAS CRÍTICAS:
1. SEMPRE retorne APENAS JSON válido, nunca texto puro
2. Se cliente pedir MÚLTIPLOS produtos: coloque TODOS no array "itens"
3. Se cliente PERSONALIZAR (tirar/adicionar ingrediente): use "acao": "adicionar" com o item e removidos/adicionais preenchidos
4. Se não houver ação: use "acao": "nenhuma" e "itens": []

EXEMPLOS DE PERSONALIZAÇÃO:
- Cliente: "tira o molho da pizza" → {{"resposta": "Anotado! Pizza sem molho.", "acao": "adicionar", "itens": [{{"nome": "Pizza Calabresa", "quantidade": 1, "removidos": ["Molho de Tomate"], "adicionais": []}}]}}
- Cliente: "quero pizza sem cebola" → {{"resposta": "Pizza sem cebola, anotado!", "acao": "adicionar", "itens": [{{"nome": "Pizza Calabresa", "quantidade": 1, "removidos": ["Cebola"], "adicionais": []}}]}}"""

        # Monta mensagens para a API
        messages = [{"role": "system", "content": system_prompt}]

        # Adiciona últimas mensagens do histórico (máximo 10)
        for msg in historico[-10:]:
            messages.append(msg)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500,
                }

                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }

                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    resposta_ia = result["choices"][0]["message"]["content"].strip()

                    # Tenta parsear JSON
                    try:
                        # Remove possíveis marcadores de código
                        resposta_limpa = resposta_ia.replace("```json", "").replace("```", "").strip()
                        print(f"📨 Resposta IA (primeiros 200 chars): {resposta_limpa[:200]}")
                        resposta_json = json.loads(resposta_limpa)

                        resposta_texto = resposta_json.get("resposta", resposta_ia)
                        acao = resposta_json.get("acao", "nenhuma")
                        print(f"🎯 Ação: {acao}")

                        # Suporta tanto "itens" (array) quanto "item" (singular) para compatibilidade
                        itens = resposta_json.get("itens", [])
                        item_singular = resposta_json.get("item")
                        if item_singular and not itens:
                            itens = [item_singular]
                        print(f"📦 Itens recebidos: {itens}")

                        # Processa ação
                        mostrar_resumo = False
                        if acao == "adicionar" and itens:
                            # Processa cada item da lista
                            for item in itens:
                                # Busca produto no cardápio para pegar preço correto
                                produto_encontrado = self._buscar_produto_por_termo(item.get("nome", ""), todos_produtos)
                                if produto_encontrado:
                                    nome_produto = produto_encontrado["nome"]
                                    removidos = item.get("removidos", [])
                                    adicionais = item.get("adicionais", [])

                                    # Verifica se o item já existe no contexto
                                    item_existente = None
                                    for p in pedido_contexto:
                                        if p["nome"].lower() == nome_produto.lower():
                                            item_existente = p
                                            break

                                    if item_existente:
                                        # Atualiza item existente (personalização ou quantidade)
                                        if removidos:
                                            item_existente["removidos"] = removidos
                                        if adicionais:
                                            item_existente["adicionais"] = adicionais
                                        # Atualiza quantidade se for diferente
                                        nova_qtd = item.get("quantidade", 1)
                                        if nova_qtd != item_existente.get("quantidade", 1):
                                            item_existente["quantidade"] = nova_qtd
                                        print(f"✏️ Item atualizado no contexto: {item_existente}")
                                    else:
                                        # Adiciona novo item
                                        novo_item = {
                                            "id": produto_encontrado.get("id", ""),
                                            "nome": nome_produto,
                                            "quantidade": item.get("quantidade", 1),
                                            "preco": produto_encontrado["preco"],
                                            "removidos": removidos,
                                            "adicionais": adicionais
                                        }
                                        pedido_contexto.append(novo_item)
                                        print(f"🛒 Item adicionado ao contexto: {novo_item}")
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

                        elif acao == "prosseguir_entrega":
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
                            total = sum(item.get('preco', 0) * item.get('quantidade', 1) for item in pedido_contexto)
                            resumo = f"\n\n📋 *Seu pedido até agora:*\n"
                            for item in pedido_contexto:
                                qtd = item.get('quantidade', 1)
                                nome = item.get('nome', '')
                                preco_unit = item.get('preco', 0)
                                preco_total = preco_unit * qtd
                                resumo += f"• {qtd}x {nome} - R$ {preco_total:.2f}\n"
                                if item.get('removidos'):
                                    resumo += f"  _Sem: {', '.join(item['removidos'])}_\n"
                                if item.get('adicionais'):
                                    resumo += f"  _Com: {', '.join(item['adicionais'])}_\n"
                            resumo += f"\n💰 *Total: R$ {total:.2f}*"
                            resposta_limpa += resumo

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
                    return "Desculpe, tive um problema. Pode repetir?"

        except Exception as e:
            print(f"❌ Erro na conversa IA: {e}")
            return "Ops, algo deu errado. Tenta de novo? 😅"

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
        carrinho = []
        for item in pedido_contexto:
            carrinho_item = {
                "id": item.get("id", ""),
                "nome": item["nome"],
                "preco": item["preco"],
                "quantidade": item.get("quantidade", 1),
                "personalizacoes": {
                    "removidos": item.get("removidos", []),
                    "adicionais": item.get("adicionais", []),
                    "preco_adicionais": 0.0
                }
            }
            carrinho.append(carrinho_item)
        return carrinho

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
        if not produtos:
            return "Ops, não encontrei produtos disponíveis no momento 😅"

        # Agrupa produtos por categoria (baseado no nome)
        pizzas = []
        bebidas = []
        lanches = []
        outros = []

        for p in produtos:
            nome_lower = p['nome'].lower()
            if 'pizza' in nome_lower:
                pizzas.append(p)
            elif any(x in nome_lower for x in ['coca', 'refri', 'suco', 'água', 'agua', 'cerveja', 'guarana', 'guaraná']):
                bebidas.append(p)
            elif any(x in nome_lower for x in ['x-', 'x ', 'burger', 'lanche', 'hamburguer', 'hambúrguer']):
                lanches.append(p)
            else:
                outros.append(p)

        mensagem = "📋 *Nosso Cardápio:*\n\n"

        if pizzas:
            mensagem += "🍕 *Pizzas:*\n"
            for p in pizzas:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        if lanches:
            mensagem += "🍔 *Lanches:*\n"
            for p in lanches:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        if bebidas:
            mensagem += "🥤 *Bebidas:*\n"
            for p in bebidas:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        if outros:
            mensagem += "📦 *Outros:*\n"
            for p in outros:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        # Se tem carrinho, mostra o que já foi adicionado
        if carrinho:
            total = sum(item['preco'] * item.get('quantidade', 1) for item in carrinho)
            mensagem += f"🛒 *Seu carrinho:* R$ {total:.2f}\n\n"

        mensagem += "É só me dizer o que você quer! 😊"

        return mensagem

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

    def _adicionar_ao_carrinho(self, dados: Dict, produto: Dict, quantidade: int = 1) -> bool:
        """
        Adiciona um produto ao carrinho com suporte a personalizações
        """
        carrinho = dados.get('carrinho', [])

        # Verifica se produto já está no carrinho (sem personalizações)
        for item in carrinho:
            if item['id'] == produto['id'] and not item.get('personalizacoes'):
                item['quantidade'] = item.get('quantidade', 1) + quantidade
                dados['carrinho'] = carrinho
                print(f"🛒 Quantidade atualizada: {item['nome']} x{item['quantidade']}")
                return True

        # Adiciona novo item com estrutura para personalizações
        novo_item = {
            'id': produto['id'],
            'nome': produto['nome'],
            'preco': produto['preco'],
            'quantidade': quantidade,
            'personalizacoes': {
                'removidos': [],      # Ingredientes removidos
                'adicionais': [],     # Adicionais incluídos [{'nome': x, 'preco': y}]
                'preco_adicionais': 0.0  # Soma dos adicionais
            }
        }
        carrinho.append(novo_item)
        dados['carrinho'] = carrinho
        dados['ultimo_produto_adicionado'] = produto['nome']  # Para referência
        print(f"🛒 Produto adicionado: {produto['nome']} - R$ {produto['preco']:.2f}")
        return True

    def _personalizar_item_carrinho(
        self,
        dados: Dict,
        acao: str,
        item_nome: str,
        produto_busca: str = None
    ) -> Tuple[bool, str]:
        """
        Personaliza um item no carrinho (remove ingrediente ou adiciona extra)

        Args:
            dados: Dados da conversa com carrinho
            acao: 'remover_ingrediente' ou 'adicionar_extra'
            item_nome: Nome do ingrediente/adicional
            produto_busca: Nome do produto (opcional, usa último adicionado)

        Returns:
            (sucesso, mensagem)
        """
        carrinho = dados.get('carrinho', [])

        if not carrinho:
            return (False, "Seu carrinho está vazio! Primeiro adicione um produto 😊")

        # Encontra o produto no carrinho
        produto_alvo = None
        if produto_busca:
            # Busca pelo nome
            for item in carrinho:
                if produto_busca.lower() in item['nome'].lower():
                    produto_alvo = item
                    break
        else:
            # Usa o último adicionado
            produto_alvo = carrinho[-1]

        if not produto_alvo:
            return (False, f"Não encontrei '{produto_busca}' no seu carrinho 🤔")

        # Inicializa personalizacoes se não existir
        if 'personalizacoes' not in produto_alvo:
            produto_alvo['personalizacoes'] = {
                'removidos': [],
                'adicionais': [],
                'preco_adicionais': 0.0
            }

        personalizacoes = produto_alvo['personalizacoes']

        if acao == "remover_ingrediente":
            # Verifica se o ingrediente existe na receita
            ingrediente = self.ingredientes_service.verificar_ingrediente_na_receita_por_nome(
                produto_alvo['nome'], item_nome
            )

            if ingrediente:
                if ingrediente['nome'] not in personalizacoes['removidos']:
                    personalizacoes['removidos'].append(ingrediente['nome'])
                    dados['carrinho'] = carrinho
                    return (True, f"✅ Ok! *{produto_alvo['nome']}* SEM {ingrediente['nome']} 👍")
                else:
                    return (True, f"Esse já tá sem {ingrediente['nome']}! 😊")
            else:
                return (False, f"Hmm, {produto_alvo['nome']} não leva {item_nome} 🤔")

        elif acao == "adicionar_extra":
            # Busca o adicional
            adicional = self.ingredientes_service.buscar_adicional_por_nome(item_nome)

            if adicional:
                # Verifica se já foi adicionado
                for add in personalizacoes['adicionais']:
                    if add['nome'].lower() == adicional['nome'].lower():
                        return (True, f"Já adicionei {adicional['nome']}! 😊")

                # Adiciona
                personalizacoes['adicionais'].append({
                    'id': adicional['id'],
                    'nome': adicional['nome'],
                    'preco': adicional['preco']
                })
                personalizacoes['preco_adicionais'] += adicional['preco']
                dados['carrinho'] = carrinho

                return (True, f"✅ Adicionei *{adicional['nome']}* (+R$ {adicional['preco']:.2f}) no seu *{produto_alvo['nome']}* 👍")
            else:
                # Lista os adicionais disponíveis
                todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
                if todos_adicionais:
                    nomes = [a['nome'] for a in todos_adicionais[:5]]
                    return (False, f"Não encontrei esse adicional 🤔\n\nTemos disponível: {', '.join(nomes)}")
                return (False, f"Não encontrei esse adicional 🤔")

        return (False, "Não entendi a personalização 😅")

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

    def _remover_do_carrinho(self, dados: Dict, produto: Dict, quantidade: int = None) -> Tuple[bool, str]:
        """
        Remove um produto do carrinho
        Returns: (sucesso, mensagem)
        """
        carrinho = dados.get('carrinho', [])

        for i, item in enumerate(carrinho):
            if item['id'] == produto['id']:
                if quantidade is None or quantidade >= item.get('quantidade', 1):
                    # Remove completamente
                    nome_removido = item['nome']
                    carrinho.pop(i)
                    dados['carrinho'] = carrinho
                    print(f"🗑️ Produto removido: {nome_removido}")
                    return True, f"✅ *{nome_removido}* removido do carrinho!"
                else:
                    # Reduz quantidade
                    item['quantidade'] = item.get('quantidade', 1) - quantidade
                    dados['carrinho'] = carrinho
                    print(f"🛒 Quantidade reduzida: {item['nome']} x{item['quantidade']}")
                    return True, f"✅ Reduzi para {item['quantidade']}x *{item['nome']}*"

        return False, f"Hmm, não encontrei *{produto['nome']}* no seu carrinho 🤔"

    def _formatar_carrinho(self, carrinho: List[Dict]) -> str:
        """Formata o carrinho para exibição, incluindo personalizações"""
        if not carrinho:
            return "🛒 Seu carrinho está vazio!"

        msg = "🛒 *Seu carrinho:*\n\n"
        total = 0
        for item in carrinho:
            qtd = item.get('quantidade', 1)
            preco_base = item['preco']
            preco_adicionais = item.get('personalizacoes', {}).get('preco_adicionais', 0.0)
            subtotal = (preco_base + preco_adicionais) * qtd
            total += subtotal

            msg += f"• {qtd}x {item['nome']} - R$ {subtotal:.2f}\n"

            # Mostra personalizações se houver
            personalizacoes = item.get('personalizacoes', {})
            removidos = personalizacoes.get('removidos', [])
            adicionais = personalizacoes.get('adicionais', [])

            if removidos:
                msg += f"  └ _SEM: {', '.join(removidos)}_\n"

            if adicionais:
                for add in adicionais:
                    msg += f"  └ _+ {add['nome']} (+R$ {add['preco']:.2f})_\n"

        msg += f"\n💰 *Total: R$ {total:.2f}*"
        return msg

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

    def _buscar_produtos(self, termo_busca: str = "") -> List[Dict[str, Any]]:
        """Busca produtos no banco de dados usando SQL direto"""
        try:
            from sqlalchemy import text

            if termo_busca:
                query = text("""
                    SELECT p.cod_barras, p.descricao, pe.preco_venda
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    AND p.descricao ILIKE :termo
                    ORDER BY p.descricao
                    LIMIT 10
                """)
                result = self.db.execute(query, {"empresa_id": self.empresa_id, "termo": f"%{termo_busca}%"})
            else:
                query = text("""
                    SELECT p.cod_barras, p.descricao, pe.preco_venda
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    ORDER BY p.descricao
                    LIMIT 10
                """)
                result = self.db.execute(query, {"empresa_id": self.empresa_id})

            return [
                {
                    "id": row[0],
                    "nome": row[1],
                    "preco": float(row[2])
                }
                for row in result.fetchall()
            ]
        except Exception as e:
            print(f"Erro ao buscar produtos: {e}")
            return []

    def _buscar_promocoes(self) -> List[Dict[str, Any]]:
        """Busca produtos em promoção/destaque usando SQL direto (prioriza receitas)"""
        try:
            from sqlalchemy import text

            produtos = []

            # Primeiro busca receitas (pizzas, lanches) - são os destaques
            query_receitas = text("""
                SELECT id, nome, preco_venda
                FROM catalogo.receitas
                WHERE empresa_id = :empresa_id
                AND ativo = true
                AND disponivel = true
                ORDER BY nome
                LIMIT 3
            """)
            result_receitas = self.db.execute(query_receitas, {"empresa_id": self.empresa_id})

            for row in result_receitas.fetchall():
                produtos.append({
                    "id": f"receita_{row[0]}",
                    "nome": row[1],
                    "preco": float(row[2]) if row[2] else 0.0
                })

            # Se não tiver receitas suficientes, busca produtos
            if len(produtos) < 3:
                query_produtos = text("""
                    SELECT p.cod_barras, p.descricao, pe.preco_venda
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    ORDER BY p.descricao
                    LIMIT :limit
                """)
                result_produtos = self.db.execute(query_produtos, {
                    "empresa_id": self.empresa_id,
                    "limit": 5 - len(produtos)
                })

                for row in result_produtos.fetchall():
                    produtos.append({
                        "id": row[0],
                        "nome": row[1],
                        "preco": float(row[2])
                    })

            return produtos[:5]
        except Exception as e:
            print(f"Erro ao buscar promoções: {e}")
            return []

    def _obter_estado_conversa(self, user_id: str) -> Tuple[str, Dict[str, Any]]:
        """Obtém estado salvo da conversa"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT metadata
                FROM chatbot.conversations
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
            """)

            result = self.db.execute(query, {"user_id": user_id}).fetchone()

            if result and result[0]:
                metadata = result[0]
                estado = metadata.get('sales_state', STATE_WELCOME)
                dados = metadata.get('sales_data', {})
                return (estado, dados)

            return (STATE_WELCOME, {'carrinho': [], 'historico': []})
        except Exception as e:
            print(f"Erro ao obter estado: {e}")
            return (STATE_WELCOME, {'carrinho': [], 'historico': []})

    def _salvar_estado_conversa(self, user_id: str, estado: str, dados: Dict[str, Any]):
        """Salva estado da conversa (cria se não existir)"""
        try:
            from sqlalchemy import text

            dados_json = json.dumps(dados, ensure_ascii=False)

            # Primeiro tenta atualizar registro existente
            query_update = text("""
                UPDATE chatbot.conversations
                SET
                    metadata = jsonb_build_object(
                        'sales_state', CAST(:estado AS text),
                        'sales_data', CAST(:dados AS jsonb)
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id
                AND id = (
                    SELECT id FROM chatbot.conversations
                    WHERE user_id = :user_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                RETURNING id
            """)

            result = self.db.execute(query_update, {
                "estado": estado,
                "dados": dados_json,
                "user_id": user_id
            })

            updated_row = result.fetchone()

            # Se não atualizou nenhum registro, cria um novo
            if not updated_row:
                import uuid
                session_id = str(uuid.uuid4())

                query_insert = text("""
                    INSERT INTO chatbot.conversations
                    (session_id, user_id, empresa_id, model, prompt_key, metadata, created_at, updated_at)
                    VALUES
                    (:session_id, :user_id, :empresa_id, 'llama-3.1-8b-instant', 'default',
                     jsonb_build_object('sales_state', CAST(:estado AS text), 'sales_data', CAST(:dados AS jsonb)),
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """)

                self.db.execute(query_insert, {
                    "session_id": session_id,
                    "user_id": user_id,
                    "empresa_id": self.empresa_id,
                    "estado": estado,
                    "dados": dados_json
                })
                print(f"📝 Nova conversa criada para {user_id}")

            self.db.commit()
        except Exception as e:
            print(f"Erro ao salvar estado: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()

    def _buscar_todos_produtos(self) -> List[Dict[str, Any]]:
        """Busca TODOS os produtos disponíveis no banco usando SQL direto (produtos + receitas)"""
        try:
            from sqlalchemy import text

            produtos = []

            # 1. Busca produtos simples (bebidas, etc)
            query_produtos = text("""
                SELECT p.cod_barras, p.descricao, pe.preco_venda
                FROM catalogo.produtos p
                JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                WHERE pe.empresa_id = :empresa_id
                AND p.ativo = true
                AND pe.disponivel = true
                ORDER BY p.descricao
            """)
            result_produtos = self.db.execute(query_produtos, {"empresa_id": self.empresa_id})

            for row in result_produtos.fetchall():
                produtos.append({
                    "id": row[0],
                    "nome": row[1],
                    "preco": float(row[2]),
                    "tipo": "produto"
                })

            # 2. Busca receitas (pizzas, lanches, etc)
            query_receitas = text("""
                SELECT id, nome, preco_venda, descricao
                FROM catalogo.receitas
                WHERE empresa_id = :empresa_id
                AND ativo = true
                AND disponivel = true
                ORDER BY nome
            """)
            result_receitas = self.db.execute(query_receitas, {"empresa_id": self.empresa_id})

            for row in result_receitas.fetchall():
                produtos.append({
                    "id": f"receita_{row[0]}",  # Prefixo para diferenciar
                    "nome": row[1],
                    "preco": float(row[2]) if row[2] else 0.0,
                    "descricao": row[3],
                    "tipo": "receita"
                })

            return produtos
        except Exception as e:
            print(f"Erro ao buscar todos produtos: {e}")
            import traceback
            traceback.print_exc()
            return []

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
                subtotal = item['preco'] * item.get('quantidade', 1)
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

        # Adiciona mensagem atual ao histórico
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

            mensagem = self.address_service.formatar_lista_enderecos_para_chat(enderecos)
            mensagem += "\n*Quer usar um desses endereços?*\n\n"
            mensagem += "📌 Digite o *número* do endereço (ex: 1, 2, 3...)\n"
            mensagem += "🆕 Ou digite *NOVO* para cadastrar outro endereço"

            return mensagem
        else:
            # Cliente não tem endereços - pedir para digitar direto
            self._salvar_estado_conversa(user_id, STATE_BUSCANDO_ENDERECO_GOOGLE, dados)

            mensagem = "📍 Agora preciso do endereço de entrega!\n\n"
            mensagem += "Digite seu endereço completo com rua, número e bairro:\n"
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

            # Ir para pagamento
            self._salvar_estado_conversa(user_id, STATE_COLETANDO_PAGAMENTO, dados)

            return f"✅ Endereço selecionado:\n📍 {endereco_selecionado['endereco_completo']}\n\n" + self._mensagem_formas_pagamento()

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

        # Ir para pagamento
        self._salvar_estado_conversa(user_id, STATE_COLETANDO_PAGAMENTO, dados)

        return f"✅ Endereço salvo!\n📍 {endereco_completo}\n\n" + self._mensagem_formas_pagamento()

    def _mensagem_formas_pagamento(self) -> str:
        """Retorna a mensagem padrão de formas de pagamento"""
        return """Agora me fala, como vai ser o pagamento?

💳 *Formas disponíveis:*
1️⃣ PIX (paga agora)
2️⃣ Dinheiro na entrega
3️⃣ Cartão na entrega

Digite o número da opção!"""

    # ========== FLUXO ENTREGA/RETIRADA ==========

    def _perguntar_entrega_ou_retirada(self, user_id: str, dados: Dict) -> str:
        """
        Pergunta ao cliente se é para entrega ou retirada
        """
        self._salvar_estado_conversa(user_id, STATE_PERGUNTANDO_ENTREGA_RETIRADA, dados)

        return """Show! Agora me diz: é pra *entrega* ou você vai *retirar* na loja? 🏍️

1️⃣ *Entrega* - levo até você
2️⃣ *Retirada* - você busca aqui

Qual vai ser?"""

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
            self._salvar_estado_conversa(user_id, STATE_COLETANDO_PAGAMENTO, dados)

            print("🏪 Cliente escolheu RETIRADA, indo para pagamento")
            return "Beleza! Você vai retirar aqui na loja 🏪\n\n" + self._mensagem_formas_pagamento()

        else:
            # Não entendeu
            return "Não entendi 😅\nDigite *1* pra entrega ou *2* pra retirada na loja"

    async def _processar_pagamento(self, user_id: str, mensagem: str, dados: Dict) -> str:
        """
        Processa a forma de pagamento escolhida
        Aceita números (1, 2, 3) ou linguagem natural (pix, dinheiro, cartao)
        """
        # Primeiro tenta detectar por linguagem natural
        forma_natural = self._detectar_forma_pagamento_natural(mensagem)
        if forma_natural:
            dados['forma_pagamento'] = forma_natural
            return await self._gerar_resumo_pedido(user_id, dados)

        # Tenta por número (incluindo ordinais)
        numero = self._extrair_numero_natural(mensagem, max_opcoes=3)

        formas = {
            1: 'PIX',
            2: 'DINHEIRO',
            3: 'CARTAO'
        }

        forma_pagamento = formas.get(numero)

        if not forma_pagamento:
            return "Ops! Escolhe uma das opções:\n*1* - PIX\n*2* - Dinheiro\n*3* - Cartão\n\nOu digite diretamente: *pix*, *dinheiro* ou *cartão* 😊"

        dados['forma_pagamento'] = forma_pagamento

        # Gerar resumo do pedido
        return await self._gerar_resumo_pedido(user_id, dados)

    async def _gerar_resumo_pedido(self, user_id: str, dados: Dict) -> str:
        """Gera o resumo final do pedido"""
        carrinho = dados.get('carrinho', [])
        endereco = dados.get('endereco_texto', 'Não informado')
        forma_pagamento = dados.get('forma_pagamento', 'PIX')
        tipo_entrega = dados.get('tipo_entrega', 'ENTREGA')

        if not carrinho:
            return "Ops, seu carrinho está vazio! Me diz o que você quer pedir 😊"

        # Calcular totais
        subtotal = sum(item['preco'] * item.get('quantidade', 1) for item in carrinho)

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

        # Montar mensagem
        mensagem = "📋 *RESUMO DO PEDIDO*\n\n"
        mensagem += "*Itens:*\n"
        for item in carrinho:
            qtd = item.get('quantidade', 1)
            subtotal_item = item['preco'] * qtd
            mensagem += f"• {qtd}x {item['nome']} - R$ {subtotal_item:.2f}\n"

        # Mostrar tipo de entrega
        if tipo_entrega == 'RETIRADA':
            mensagem += f"\n🏪 *Retirada na loja*\n"
        else:
            mensagem += f"\n📍 *Endereço:* {endereco}\n"

        mensagem += f"💳 *Pagamento:* {forma_pagamento}\n\n"

        mensagem += f"Subtotal: R$ {subtotal:.2f}\n"
        if taxa_entrega > 0:
            mensagem += f"Taxa de entrega: R$ {taxa_entrega:.2f}\n"
        mensagem += f"\n*TOTAL: R$ {total:.2f}*\n\n"

        mensagem += "✅ Digite *OK* para confirmar o pedido\n"
        mensagem += "❌ Ou *CANCELAR* para desistir"

        return mensagem

    async def _salvar_pedido_via_checkout(self, user_id: str, dados: Dict) -> Optional[int]:
        """
        Salva o pedido chamando o endpoint /checkout via HTTP

        Args:
            user_id: Telefone do cliente (WhatsApp)
            dados: Dados da conversa com carrinho, endereço, etc

        Returns:
            ID do pedido criado ou None se falhar
        """
        try:
            carrinho = dados.get('carrinho', [])
            if not carrinho:
                print("[Checkout] Carrinho vazio, nada a salvar")
                return None

            # Dados do pedido
            tipo_entrega = dados.get('tipo_entrega', 'ENTREGA')
            endereco_id = dados.get('endereco_id')
            forma_pagamento = dados.get('forma_pagamento', 'PIX')

            # Buscar ou criar cliente para obter o super_token
            cliente = self.address_service.criar_cliente_se_nao_existe(user_id)
            if not cliente:
                print("[Checkout] ERRO: Não foi possível criar/buscar cliente")
                return None

            super_token = cliente.get('super_token')
            if not super_token:
                print("[Checkout] ERRO: Cliente sem super_token")
                return None

            # Mapear tipo_entrega do chatbot para ENUM do checkout
            # Para ENTREGA em casa: tipo_pedido = DELIVERY
            # Para RETIRADA na loja: tipo_pedido = BALCAO (o schema força tipo_entrega=DELIVERY quando tipo_pedido=DELIVERY)
            if tipo_entrega == 'ENTREGA':
                tipo_pedido = "DELIVERY"
                tipo_entrega_enum = "DELIVERY"
            else:
                tipo_pedido = "BALCAO"  # Para retirada na loja
                tipo_entrega_enum = "RETIRADA"

            # Montar payload do checkout
            # Separa produtos (cod_barras) de receitas (receita_ID)
            itens_checkout = []
            receitas_checkout = []

            for item in carrinho:
                item_id = item.get('id', '')
                quantidade = item.get('quantidade', 1)
                observacao = item.get('observacoes')

                # Se o ID começa com "receita_", é uma receita
                if isinstance(item_id, str) and item_id.startswith('receita_'):
                    receita_id = int(item_id.replace('receita_', ''))
                    receitas_checkout.append({
                        "receita_id": receita_id,
                        "quantidade": quantidade,
                        "observacao": observacao
                    })
                else:
                    # É um produto com código de barras
                    itens_checkout.append({
                        "produto_cod_barras": item_id,
                        "quantidade": quantidade,
                        "observacao": observacao
                    })

            # Monta o payload com itens e/ou receitas
            produtos_payload = {}
            if itens_checkout:
                produtos_payload["itens"] = itens_checkout
            if receitas_checkout:
                produtos_payload["receitas"] = receitas_checkout

            payload = {
                "empresa_id": self.empresa_id,
                "tipo_pedido": tipo_pedido,
                "tipo_entrega": tipo_entrega_enum,
                "origem": "APP",  # WhatsApp = APP
                "produtos": produtos_payload
            }

            # Adiciona endereço apenas se for entrega
            if tipo_entrega == 'ENTREGA' and endereco_id:
                payload["endereco_id"] = endereco_id

            # Mapear forma de pagamento para meio_pagamento_id
            # TODO: Buscar meio_pagamento_id do banco baseado na forma escolhida
            # Por enquanto vamos deixar sem meio de pagamento (será selecionado depois)
            # meios_pagamento = []
            # if forma_pagamento:
            #     meios_pagamento.append({"id": 1, "valor": total})
            # payload["meios_pagamento"] = meios_pagamento

            print(f"[Checkout] Payload: {json.dumps(payload, indent=2)}")

            # Chamar endpoint /checkout
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Content-Type": "application/json",
                    "X-Super-Token": super_token
                }

                # URL do checkout (localhost pois estamos no mesmo servidor)
                checkout_url = "http://localhost:8002/api/pedidos/client/checkout"

                print(f"[Checkout] Chamando {checkout_url}")
                response = await client.post(checkout_url, json=payload, headers=headers)

                print(f"[Checkout] Status: {response.status_code}")

                if response.status_code == 201:
                    result = response.json()
                    pedido_id = result.get('id')
                    print(f"[Checkout] ✅ Pedido criado com sucesso! ID: {pedido_id}")
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

    def _salvar_pedido_no_banco(self, user_id: str, dados: Dict) -> Optional[int]:
        """
        DEPRECATED: Use _salvar_pedido_via_checkout ao invés disso.
        Mantido apenas para compatibilidade.
        """
        # Este método agora é síncrono, mas o novo fluxo usa o async
        # Mantém o código antigo como fallback
        print("[SalvarPedido] AVISO: Método legado chamado. Use _salvar_pedido_via_checkout.")
        return None

    # ========== RESPOSTAS CONVERSACIONAIS ==========

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
        # Monta prompt conversacional
        prompt_conversa = f"""Você é um atendente simpático de delivery via WhatsApp.
Responda de forma NATURAL, CURTA (1-3 frases) e AMIGÁVEL. Use no máximo 1 emoji.

CONTEXTO:
- Tipo de conversa: {tipo_conversa}
- Carrinho do cliente: {len(carrinho)} itens, R$ {sum(i['preco']*i.get('quantidade',1) for i in carrinho):.2f}
- Histórico recente disponível

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

                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }

                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    resposta = result["choices"][0]["message"]["content"].strip()

                    # Limpa respostas muito longas
                    if len(resposta) > 300:
                        resposta = resposta[:300] + "..."

                    # Salva no histórico
                    historico = dados.get('historico', [])
                    historico.append({"role": "user", "content": mensagem})
                    historico.append({"role": "assistant", "content": resposta})
                    dados['historico'] = historico[-10:]
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)

                    return resposta

        except Exception as e:
            print(f"❌ Erro na conversa: {e}")

        # Fallback para respostas padrão por tipo
        fallbacks = {
            "saudacao": "E aí! Tudo bem? 😊 O que vai ser hoje?",
            "pergunta_vaga": "Temos várias opções! Quer uma pizza, lanche ou bebida?",
            "pedido_sugestao": "Recomendo nosso X-Bacon, tá fazendo sucesso! Ou prefere pizza?",
            "duvida_geral": "Como posso te ajudar?",
            "resposta_generica": "Entendi! O que você gostaria de pedir?",
            "nao_entendi": "Hmm, não entendi. 🤔 Quer ver o cardápio ou prefere uma sugestão?"
        }
        return fallbacks.get(tipo_conversa, "O que você gostaria de pedir?")

    async def _gerar_resposta_sobre_produto(
        self,
        user_id: str,
        produto: Dict,
        pergunta: str,
        dados: Dict
    ) -> str:
        """
        Gera resposta sobre um produto específico.
        Usa ingredientes REAIS do banco de dados!
        """
        # Busca ingredientes reais do banco de dados
        ingredientes = self.ingredientes_service.buscar_ingredientes_por_nome_receita(produto['nome'])
        adicionais = self.ingredientes_service.buscar_adicionais_por_nome_receita(produto['nome'])

        # Se encontrou ingredientes, usa dados reais
        if ingredientes:
            nomes_ingredientes = [ing['nome'] for ing in ingredientes]

            # Monta resposta com ingredientes reais
            msg = f"*{produto['nome']}* - R$ {produto['preco']:.2f}\n\n"
            msg += "📋 *Ingredientes:*\n"
            for ing in ingredientes:
                msg += f"• {ing['nome']}\n"

            if adicionais:
                msg += "\n➕ *Adicionais disponíveis:*\n"
                for add in adicionais[:4]:  # Mostra até 4 adicionais
                    msg += f"• {add['nome']} (+R$ {add['preco']:.2f})\n"

            msg += "\nQuer pedir? 😊"
            return msg

        # Se não encontrou ingredientes no banco, usa IA para resposta genérica
        prompt = f"""Você é um atendente de delivery. O cliente quer saber sobre:

PRODUTO: {produto['nome']} - R$ {produto['preco']:.2f}

PERGUNTA DO CLIENTE: {pergunta if pergunta else 'quer saber mais sobre o produto'}

Responda de forma CURTA e ÚTIL (2-3 frases máximo).
Se não souber detalhes específicos, dê uma resposta genérica positiva.
Termine perguntando se quer pedir.

Responda:"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 100,
                }

                headers = {
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }

                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"❌ Erro ao informar produto: {e}")

        # Fallback
        return f"{produto['nome']} é uma ótima escolha! Custa R$ {produto['preco']:.2f}. Quer adicionar ao pedido?"

    # ========== PROCESSAMENTO PRINCIPAL ==========

    async def processar_mensagem(self, user_id: str, mensagem: str) -> str:
        """
        Processa mensagem usando Groq API com fluxo de endereços integrado
        """
        try:
            # Obtém estado atual
            estado, dados = self._obter_estado_conversa(user_id)
            print(f"📊 Estado atual: {estado}")

            # Se for primeira mensagem (saudação), entra no modo conversacional
            if self._eh_primeira_mensagem(mensagem):
                dados['historico'] = [{"role": "user", "content": mensagem}]
                dados['carrinho'] = []
                dados['pedido_contexto'] = []  # Lista de itens mencionados na conversa
                dados['produtos_encontrados'] = self._buscar_promocoes()
                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                return self._gerar_mensagem_boas_vindas_conversacional()

            # ========== MODO CONVERSACIONAL (IA LIVRE) ==========
            if estado == STATE_CONVERSANDO:
                return await self._processar_conversa_ia(user_id, mensagem, dados)

            # ========== FLUXO DE ENTREGA/RETIRADA ==========

            # Estado: Perguntando se é entrega ou retirada
            if estado == STATE_PERGUNTANDO_ENTREGA_RETIRADA:
                return await self._processar_entrega_ou_retirada(user_id, mensagem, dados)

            # ========== FLUXO DE ENDEREÇOS ==========

            # Estado: Listando endereços salvos (cliente escolhe número ou "NOVO")
            if estado == STATE_LISTANDO_ENDERECOS:
                return await self._processar_selecao_endereco_salvo(user_id, mensagem, dados)

            # Estado: Buscando endereço no Google Maps
            if estado == STATE_BUSCANDO_ENDERECO_GOOGLE:
                return await self._processar_busca_endereco_google(user_id, mensagem, dados)

            # Estado: Selecionando endereço do Google
            if estado == STATE_SELECIONANDO_ENDERECO_GOOGLE:
                return await self._processar_selecao_endereco_google(user_id, mensagem, dados)

            # Estado: Coletando complemento
            if estado == STATE_COLETANDO_COMPLEMENTO:
                return await self._processar_complemento(user_id, mensagem, dados)

            # Estado: Coletando pagamento
            if estado == STATE_COLETANDO_PAGAMENTO:
                return await self._processar_pagamento(user_id, mensagem, dados)

            # Estado: Confirmando pedido
            if estado == STATE_CONFIRMANDO_PEDIDO:
                if self._detectar_confirmacao_pedido(mensagem):
                    # Salvar pedido via endpoint /checkout
                    resultado = await self._salvar_pedido_via_checkout(user_id, dados)

                    if isinstance(resultado, dict) and resultado.get('erro'):
                        # Checkout falhou - mostrar erro ao usuário
                        erro_msg = resultado.get('mensagem', 'Erro ao processar pedido')
                        return f"❌ *Ops! Não foi possível confirmar o pedido:*\n\n{erro_msg}\n\nDigite *OK* para tentar novamente ou *CANCELAR* para desistir."

                    # Sucesso - limpar carrinho e resetar estado
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)

                    if resultado:
                        return f"🎉 *PEDIDO CONFIRMADO!*\n\n📋 Número do pedido: *#{resultado}*\n\nSeu pedido foi enviado para a cozinha!\nVocê receberá atualizações sobre a entrega.\n\nObrigado pela preferência! 😊"
                    else:
                        return "🎉 *PEDIDO CONFIRMADO!*\n\nSeu pedido foi enviado para a cozinha!\nVocê receberá atualizações sobre a entrega.\n\nObrigado pela preferência! 😊"
                elif 'cancelar' in mensagem.lower():
                    dados['carrinho'] = []
                    self._salvar_estado_conversa(user_id, STATE_WELCOME, dados)
                    return "Tudo bem! Pedido cancelado 😊\n\nQuando quiser fazer um pedido, é só me chamar!"
                else:
                    return "Digite *OK* para confirmar ou *CANCELAR* para desistir"

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

            # ADICIONAR PRODUTO
            if funcao == "adicionar_produto":
                produto_busca = params.get("produto_busca", "")
                quantidade = params.get("quantidade", 1)

                # Busca o produto pelo termo que a IA extraiu
                produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)

                if produto:
                    self._adicionar_ao_carrinho(dados, produto, quantidade)
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                    print(f"🛒 Carrinho atual: {dados.get('carrinho', [])}")

                    carrinho = dados.get('carrinho', [])
                    total = sum(item['preco'] * item.get('quantidade', 1) for item in carrinho)

                    # Respostas variadas e naturais
                    respostas_confirmacao = [
                        f"Anotado! {quantidade}x {produto['nome']} 👍\nMais alguma coisa?",
                        f"Beleza! {produto['nome']} no carrinho! Quer mais algo?",
                        f"Show! Adicionei {produto['nome']}. E aí, vai querer mais?",
                        f"Pronto! {produto['nome']} anotado. Mais algum pedido?",
                    ]
                    import random
                    msg_resposta = random.choice(respostas_confirmacao)
                    msg_resposta += f"\n\n💰 Total até agora: R$ {total:.2f}"
                    return msg_resposta
                else:
                    return f"Hmm, não achei '{produto_busca}' aqui 🤔\n\nQuer que eu te mostre o que temos?"

            # REMOVER PRODUTO
            elif funcao == "remover_produto":
                produto_busca = params.get("produto_busca", "")
                produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)

                if produto:
                    sucesso, msg_remocao = self._remover_do_carrinho(dados, produto)
                    self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)

                    carrinho = dados.get('carrinho', [])
                    if carrinho:
                        total = sum(item['preco'] * item.get('quantidade', 1) for item in carrinho)
                        return f"Ok, tirei! 👍\nTotal agora: R$ {total:.2f}\n\nMais alguma coisa?"
                    else:
                        return "Pronto, tirei! Seu carrinho tá vazio agora.\n\nO que vai querer?"
                else:
                    return f"Não achei '{produto_busca}' no seu pedido 🤔"

            # FINALIZAR PEDIDO
            elif funcao == "finalizar_pedido":
                if carrinho:
                    print("🛒 Cliente quer finalizar, perguntando entrega ou retirada")
                    return self._perguntar_entrega_ou_retirada(user_id, dados)
                else:
                    return "Opa, seu carrinho tá vazio ainda! O que vai querer?"

            # VER CARDÁPIO
            elif funcao == "ver_cardapio":
                print("📋 Cliente pediu para ver o cardápio")
                return self._gerar_lista_produtos(todos_produtos, carrinho)

            # VER CARRINHO
            elif funcao == "ver_carrinho":
                print("🛒 Cliente pediu para ver o carrinho")
                if carrinho:
                    msg = self._formatar_carrinho(carrinho)
                    msg += "\n\nQuer mais algo ou posso fechar?"
                    return msg
                else:
                    return "Carrinho vazio ainda! O que vai ser hoje?"

            # INFORMAR SOBRE PRODUTO
            elif funcao == "informar_sobre_produto":
                produto_busca = params.get("produto_busca", "")
                pergunta = params.get("pergunta", "")
                produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)

                if produto:
                    # Gera resposta contextual sobre o produto com ingredientes reais
                    return await self._gerar_resposta_sobre_produto(user_id, produto, pergunta, dados)
                else:
                    return "Qual produto você quer saber mais? Me fala o nome!"

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

            # VER ADICIONAIS DISPONÍVEIS
            elif funcao == "ver_adicionais":
                produto_busca = params.get("produto_busca", "")

                # Se não especificou produto, usa o último do carrinho
                if not produto_busca and carrinho:
                    produto_busca = carrinho[-1]['nome']

                if produto_busca:
                    # Busca adicionais específicos para este produto
                    adicionais = self.ingredientes_service.buscar_adicionais_por_nome_receita(produto_busca)

                    if adicionais:
                        msg = f"➕ *Adicionais para {produto_busca}:*\n\n"
                        for add in adicionais:
                            msg += f"• {add['nome']} - +R$ {add['preco']:.2f}\n"
                        msg += "\nQuer adicionar algum? 😊"
                        return msg

                # Se não encontrou específicos, mostra todos
                todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
                if todos_adicionais:
                    msg = "➕ *Adicionais disponíveis:*\n\n"
                    for add in todos_adicionais:
                        msg += f"• {add['nome']} - +R$ {add['preco']:.2f}\n"
                    msg += "\nQuer adicionar algum? 😊"
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
            print("⏰ Timeout no Groq")
            return "Xiii, demorou demais... Pode mandar de novo?"

        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            import traceback
            traceback.print_exc()
            return "Ops, tive um probleminha técnico. Tenta de novo!"


# Função principal para usar no webhook
async def processar_mensagem_groq(
    db: Session,
    user_id: str,
    mensagem: str,
    empresa_id: int = 1
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
            prompt_key="default",
            model="groq-sales",
            empresa_id=empresa_id
        )
        print(f"   ✅ Nova conversa criada no banco: {conversation_id}")

    # 2. Salva mensagem do usuário no banco
    chatbot_db.create_message(db, conversation_id, "user", mensagem)

    # 3. Processa mensagem com o handler
    handler = GroqSalesHandler(db, empresa_id)
    resposta = await handler.processar_mensagem(user_id, mensagem)

    # 4. Salva resposta do bot no banco
    chatbot_db.create_message(db, conversation_id, "assistant", resposta)

    return resposta

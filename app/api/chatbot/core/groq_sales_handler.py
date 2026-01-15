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

# Configuração do Groq - API Key deve ser configurada via variável de ambiente
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"  # Modelo menor = mais limite no free tier

# Link do cardápio (configurável)
LINK_CARDAPIO = "https://chatbot.mensuraapi.com.br"

# Definição das funções que a IA pode chamar (Function Calling)
AI_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "adicionar_produto",
            "description": "Adiciona um produto ao carrinho. Use APENAS quando o cliente especifica um PRODUTO do cardápio. Exemplos: 'me ve uma coca', 'quero 2 pizzas', 'manda um x-bacon'. NÃO use para frases genéricas como 'quero fazer pedido', 'quero pedir' - nesses casos use 'conversar' para perguntar o que ele quer.",
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
            "description": "Cliente quer SABER MAIS sobre um PRODUTO ESPECÍFICO mencionado na mensagem. Use quando a pergunta menciona um produto concreto. Exemplos: 'o que vem no x-bacon?', 'o que tem no x-bacon?', 'ingredientes da pizza', 'qual o tamanho da pizza?', 'tem lactose no hamburguer?', 'o que tem na calabresa?'. NÃO use para perguntas genéricas como 'o que tem?' sem mencionar produto específico.",
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
        # Cache de meios de pagamento (carregado uma vez)
        self._meios_pagamento_cache = None

    def _buscar_meios_pagamento(self) -> List[Dict]:
        """
        Busca meios de pagamento ativos do banco de dados.
        Usa cache para evitar consultas repetidas.
        """
        if self._meios_pagamento_cache is not None:
            return self._meios_pagamento_cache

        try:
            result = self.db.execute(text("""
                SELECT id, nome, tipo
                FROM cadastros.meios_pagamento
                WHERE ativo = true
                ORDER BY id
            """))
            meios = []
            for row in result.fetchall():
                meios.append({
                    'id': row[0],
                    'nome': row[1],
                    'tipo': row[2]
                })

            # Se não houver meios cadastrados, usar fallback
            if not meios:
                meios = [
                    {'id': 1, 'nome': 'PIX', 'tipo': 'PIX_ENTREGA'},
                    {'id': 2, 'nome': 'Dinheiro', 'tipo': 'DINHEIRO'},
                    {'id': 3, 'nome': 'Cartão', 'tipo': 'CARTAO_ENTREGA'}
                ]

            self._meios_pagamento_cache = meios
            print(f"💳 Meios de pagamento carregados: {[m['nome'] for m in meios]}")
            return meios
        except Exception as e:
            print(f"❌ Erro ao buscar meios de pagamento: {e}")
            # Fallback para meios padrão
            return [
                {'id': 1, 'nome': 'PIX', 'tipo': 'PIX_ENTREGA'},
                {'id': 2, 'nome': 'Dinheiro', 'tipo': 'DINHEIRO'},
                {'id': 3, 'nome': 'Cartão', 'tipo': 'CARTAO_ENTREGA'}
            ]

    def _detectar_forma_pagamento_em_mensagem(self, mensagem: str) -> Optional[Dict]:
        """
        Detecta se a mensagem contém uma forma de pagamento.
        Retorna o meio de pagamento encontrado ou None.
        Funciona em qualquer parte do fluxo!

        IMPORTANTE: Ignora mensagens que são PERGUNTAS sobre pagamento
        (ex: "aceitam pix?", "pode ser no cartão?")
        """
        msg = mensagem.lower().strip()

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

        # Informação sobre produto ESPECÍFICO (DEVE vir ANTES da detecção genérica de "o que tem")
        # Detecta: "o que tem no X", "o que vem no X", "o que tem na X", "ingredientes do X", etc.
        if re.search(r'(o\s*q(ue)?\s*(vem|tem|ve|é)\s*(n[oa]|d[oa])|qu?al.*(ingrediente|composi[çc][aã]o)|ingredientes?\s*(d[oa])|composi[çc][aã]o)', msg):
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

        # Perguntas sobre o que tem disponível (genérico - DEVE vir DEPOIS da detecção de produto específico)
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
            # Tenta usar regras como fallback quando a IA falha
            resultado_fallback = self._interpretar_intencao_regras(mensagem, produtos, carrinho)
            if resultado_fallback:
                print(f"🔄 Usando regras como fallback após erro da IA")
                return resultado_fallback
            return {"funcao": "conversar", "params": {"tipo_conversa": "resposta_generica"}}

    def _buscar_produto_por_termo(self, termo: str, produtos: List[Dict] = None) -> Optional[Dict]:
        """
        Busca um produto usando busca inteligente no banco (produtos + receitas + combos).
        Se produtos for fornecido, também busca na lista como fallback.
        Usa busca fuzzy com correção de erros e suporte a variações.
        """
        if not termo or len(termo.strip()) < 2:
            return None
        
        termo = termo.strip()
        
        # PRIMEIRO: Tenta busca inteligente no banco (produtos + receitas + combos)
        resultados_banco = self._buscar_produtos_inteligente(termo, limit=1)
        
        if resultados_banco:
            produto_encontrado = resultados_banco[0]
            print(f"✅ Produto encontrado no banco: {produto_encontrado['nome']} (tipo: {produto_encontrado.get('tipo', 'produto')})")
            return produto_encontrado
        
        # FALLBACK: Se não encontrou no banco e tem lista de produtos, busca na lista
        if produtos:
            termo_lower = termo.lower().strip()

            # Remove acentos
            def remover_acentos(texto):
                acentos = {'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
                           'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u', 'ç': 'c'}
                for acentuado, sem_acento in acentos.items():
                    texto = texto.replace(acentuado, sem_acento)
                return texto

            # Normaliza removendo hífens, espaços e caracteres especiais
            def normalizar(texto):
                texto = remover_acentos(texto.lower())
                return re.sub(r'[-\s_.]', '', texto)

            termo_sem_acento = remover_acentos(termo_lower)
            termo_normalizado = normalizar(termo_lower)

            # 1. Match exato no nome
            for produto in produtos:
                nome_lower = produto['nome'].lower()
                nome_sem_acento = remover_acentos(nome_lower)
                if termo_lower == nome_lower or termo_sem_acento == nome_sem_acento:
                    print(f"✅ Match exato na lista: {produto['nome']}")
                    return produto

            # 1.5 Match normalizado (xbacon = x-bacon, coca cola = cocacola)
            for produto in produtos:
                nome_normalizado = normalizar(produto['nome'])
                if termo_normalizado == nome_normalizado:
                    print(f"✅ Match normalizado na lista: {produto['nome']}")
                    return produto

            # 2. Nome contém o termo (também normalizado)
            for produto in produtos:
                nome_lower = produto['nome'].lower()
                nome_sem_acento = remover_acentos(nome_lower)
                nome_normalizado = normalizar(produto['nome'])
                if termo_sem_acento in nome_sem_acento or termo_lower in nome_lower or termo_normalizado in nome_normalizado:
                    print(f"✅ Match parcial na lista (termo no nome): {produto['nome']}")
                    return produto

            # 3. Termo contém o nome do produto
            for produto in produtos:
                nome_lower = produto['nome'].lower()
                nome_sem_acento = remover_acentos(nome_lower)
                # Busca cada palavra do nome no termo
                palavras_nome = nome_sem_acento.split()
                for palavra in palavras_nome:
                    if len(palavra) > 3 and palavra in termo_sem_acento:
                        print(f"✅ Match por palavra '{palavra}' na lista: {produto['nome']}")
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
                            print(f"✅ Match por mapeamento '{chave}' na lista: {produto['nome']}")
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
        """Gera mensagem de boas-vindas para modo conversacional com botões"""
        # Busca nome da empresa e link do cardápio do banco
        try:
            empresa_query = text("""
                SELECT nome, cardapio_link
                FROM cadastros.empresas
                WHERE id = :empresa_id
            """)
            result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
            empresa = result.fetchone()
            
            nome_empresa = empresa[0] if empresa and empresa[0] else "[Nome da Empresa]"
            link_cardapio = empresa[1] if empresa and empresa[1] else LINK_CARDAPIO
        except Exception as e:
            print(f"⚠️ Erro ao buscar dados da empresa: {e}")
            nome_empresa = "[Nome da Empresa]"
            link_cardapio = LINK_CARDAPIO

        mensagem = f"👋 Olá! Seja bem-vindo(a) à {nome_empresa}!\n"
        mensagem += "É um prazer te atender 😊\n\n"
        mensagem += f"📲 Para conferir nosso cardápio completo, é só acessar o link abaixo:\n"
        mensagem += f"👉 {link_cardapio}\n\n"
        mensagem += "🛒 Prefere pedir por aqui mesmo?\n"
        mensagem += "Sem problemas! É só me dizer o que você gostaria que eu te ajudo a montar seu pedido passo a passo 😉\n\n"
        mensagem += "💬 Fico à disposição!"

        return mensagem

    async def _processar_conversa_ia(self, user_id: str, mensagem: str, dados: dict) -> str:
        """
        Processa mensagem no modo conversacional usando IA livre.
        A IA conversa naturalmente, tira dúvidas e anota o pedido.
        """
        import json
        import re

        # PRIMEIRO: Tenta interpretar com regras (funciona mesmo sem IA)
        # Isso garante que perguntas sobre produtos específicos sejam detectadas
        todos_produtos = self._buscar_todos_produtos()
        carrinho = dados.get('carrinho', [])
        pedido_contexto = dados.get('pedido_contexto', [])
        
        # ANTES DE TUDO: Detecta perguntas sobre ingredientes/composição de produtos
        # Isso funciona mesmo sem IA e deve ter prioridade
        msg_lower = mensagem.lower()
        
        # Detecta padrões como "O que vem nele", "Que tem nele" (sem mencionar produto)
        padroes_nele = [
            r'o\s+que\s+(?:vem|tem)\s+nele',
            r'que\s+(?:vem|tem)\s+nele',
            r'o\s+que\s+(?:vem|tem)\s+n[oa]\s+ele',
            r'que\s+(?:vem|tem)\s+n[oa]\s+ele'
        ]
        for padrao in padroes_nele:
            if re.search(padrao, msg_lower):
                # Se tem pedido_contexto, usa o último produto
                if pedido_contexto:
                    ultimo_produto = pedido_contexto[-1]
                    produto_encontrado = self._buscar_produto_por_termo(ultimo_produto.get('nome', ''), todos_produtos)
                    if produto_encontrado:
                        print(f"🔍 [IA] Detectada pergunta 'nele' sobre último produto: '{produto_encontrado['nome']}'")
                        return await self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                # Se não tem pedido_contexto, pergunta qual produto
                return "Qual produto você quer saber? Me fala o nome! 😊"
        
        # Detecta perguntas do tipo "tem X?" ou "vocês tem X?" - usa busca inteligente
        padrao_tem = re.search(r'(?:tem|têm|vocês?\s+tem|vcs\s+tem)\s+([a-záàâãéêíóôõúç\-\s]+?)(?:\?|$|,|\.)', msg_lower)
        if padrao_tem:
            produto_pergunta = padrao_tem.group(1).strip()
            # Remove palavras genéricas
            palavras_ignorar = ['ai', 'aí', 'no', 'cardapio', 'menu', 'aqui', 'disponivel', 'disponível']
            produto_pergunta_limpo = ' '.join([p for p in produto_pergunta.split() if p.lower() not in palavras_ignorar])
            
            if produto_pergunta_limpo and len(produto_pergunta_limpo) > 2:
                print(f"🔍 [IA] Detectada pergunta 'tem X?': '{produto_pergunta_limpo}'")
                # Usa busca inteligente diretamente no banco
                produtos_encontrados = self._buscar_produtos_inteligente(produto_pergunta_limpo, limit=3)
                if produtos_encontrados:
                    # Se encontrou exatamente 1, mostra detalhes
                    if len(produtos_encontrados) == 1:
                        produto = produtos_encontrados[0]
                        return await self._gerar_resposta_sobre_produto(user_id, produto, mensagem, dados)
                    else:
                        # Se encontrou vários, lista os principais
                        resposta = f"Sim! Temos:\n\n"
                        for i, p in enumerate(produtos_encontrados[:3], 1):
                            resposta += f"{i}. *{p['nome']}* - R$ {p['preco']:.2f}\n"
                        resposta += "\nQual você quer saber mais? 😊"
                        return resposta
                else:
                    return f"Desculpa, não encontrei '{produto_pergunta_limpo}' no cardápio. Quer ver o que temos disponível? 😊"
        
        # Detecta perguntas com nome de produto explícito
        quer_saber, nome_produto = detectar_pergunta_ingredientes(mensagem)
        if quer_saber and nome_produto:
            print(f"🔍 [IA] Detectada pergunta sobre produto: '{nome_produto}'")
            # Usa busca inteligente diretamente no banco
            produtos_encontrados = self._buscar_produtos_inteligente(nome_produto, limit=1)
            if produtos_encontrados:
                produto_encontrado = produtos_encontrados[0]
                return await self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
            else:
                # Fallback para busca na lista
                produto_encontrado = self._buscar_produto_por_termo(nome_produto, todos_produtos)
                if produto_encontrado:
                    return await self._gerar_resposta_sobre_produto(user_id, produto_encontrado, mensagem, dados)
                else:
                    return f"Hmm, não encontrei o produto '{nome_produto}' no cardápio. Quer ver o cardápio completo? 😊"
        
        # Detecta múltiplas ações na mensagem (ex: "Quero 2 xbacon. Um é sem tomate")
        acoes_detectadas = []
        msg_para_personalizacao = mensagem  # Inicializa com a mensagem original
        import re
        
        # 1. Tenta detectar adicionar produto
        resultado_adicionar = self._interpretar_intencao_regras(mensagem, todos_produtos, carrinho)
        if resultado_adicionar and resultado_adicionar.get("funcao") == "adicionar_produto":
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
                    quantidade = params.get("quantidade", 1)
                    produto = self._buscar_produto_por_termo(produto_busca, todos_produtos)
                    
                    if produto:
                        # Adiciona ao pedido_contexto no modo conversacional
                        pedido_contexto = dados.get('pedido_contexto', [])
                        for _ in range(quantidade):
                            novo_item = {
                                'id': str(produto['id']),
                                'nome': produto['nome'],
                                'preco': produto['preco'],
                                'quantidade': 1,
                                'removidos': [],
                                'adicionais': [],
                                'preco_adicionais': 0.0
                            }
                            pedido_contexto.append(novo_item)
                        
                        dados['pedido_contexto'] = pedido_contexto
                        mensagens_resposta.append(f"✅ Adicionei {quantidade}x *{produto['nome']}* ao pedido!")
                
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
        resultado_regras = self._interpretar_intencao_regras(mensagem, todos_produtos, carrinho)
        
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
                        return await self._gerar_resposta_sobre_produto(user_id, produto, pergunta, dados)
                    else:
                        return f"Não encontrei '{produto_busca}' no cardápio. Quer que eu mostre o que temos? 😊"
                elif funcao == "ver_cardapio":
                    pedido_contexto = dados.get('pedido_contexto', [])
                    return self._gerar_lista_produtos(todos_produtos, pedido_contexto)
                elif funcao == "ver_carrinho":
                    if carrinho:
                        msg = self._formatar_carrinho(carrinho)
                        msg += "\n\nQuer mais algo ou posso fechar?"
                        return msg
                    else:
                        return "Carrinho vazio ainda! O que vai ser hoje?"
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
                        # Remove possíveis marcadores de código
                        resposta_limpa = resposta_ia.replace("```json", "").replace("```", "").strip()
                        print(f"📨 Resposta IA (primeiros 200 chars): {resposta_limpa[:200]}")

                        # Tenta extrair JSON da resposta (pode ter texto antes/depois)
                        json_str = resposta_limpa
                        if not resposta_limpa.startswith('{'):
                            # Procura o início do JSON
                            json_start = resposta_limpa.find('{')
                            if json_start != -1:
                                # Encontra o final do JSON (último })
                                json_end = resposta_limpa.rfind('}')
                                if json_end != -1 and json_end > json_start:
                                    json_str = resposta_limpa[json_start:json_end + 1]
                                    print(f"🔍 JSON extraído do meio do texto")

                        resposta_json = json.loads(json_str)

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
                                if item.get('adicionais'):
                                    resumo += f"  _Complemento: {', '.join(item['adicionais'])}_\n"
                            resumo += f"\n💰 *Total: R$ {total:.2f}*"
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
                                                # Opcionais - mostra direto sem pedir SIM
                                                resposta_limpa = resposta_limpa.replace("Quer mais algo?", "").replace("Quer mais algo? 😊", "").strip()
                                                # Mostra os complementos opcionais disponíveis
                                                resposta_limpa += self.ingredientes_service.formatar_complementos_para_chat(complementos, nome_produto)
                                                resposta_limpa += "\n\n_Digite o que deseja adicionar ou continue seu pedido!_ 😊"
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
                    return self._fallback_resposta_inteligente(mensagem, dados)

        except Exception as e:
            print(f"❌ Erro na conversa IA: {e}")
            # Fallback inteligente - analisa a mensagem e responde de forma natural
            return self._fallback_resposta_inteligente(mensagem, dados)

    def _fallback_resposta_inteligente(self, mensagem: str, dados: dict) -> str:
        """
        Fallback quando a IA falha - analisa a mensagem e toma uma decisão inteligente.
        Nunca retorna erro genérico.
        """
        msg_lower = mensagem.lower().strip()
        pedido_contexto = dados.get('pedido_contexto', [])
        todos_produtos = self._buscar_todos_produtos()
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
                        resp += f"  _Complemento: {', '.join(item['adicionais'])}_\n"
                resp += f"\n💰 *Total: R$ {total:.2f}*"
                resp += "\n\nQuer mais alguma coisa? 😊"
                return resp

        # 1. Saudações - responde de forma amigável
        saudacoes = ['oi', 'olá', 'ola', 'hey', 'eae', 'e ai', 'opa', 'bom dia', 'boa tarde', 'boa noite', 'tudo bem', 'tudo bom']
        if any(s in msg_lower for s in saudacoes):
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
                            resp += f"  _Complemento: {', '.join(item['adicionais'])}_\n"
                    resp += f"\n💰 *Total: R$ {total:.2f}*"

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
                                resp += "\n\nQuer mais alguma coisa? 😊"
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
                        resp += f"  _Complemento: {', '.join(item['adicionais'])}_\n"
                resp += f"\n💰 *Total: R$ {total:.2f}*\n\nQuer mais alguma coisa? 😊"

                self._salvar_estado_conversa(user_id, STATE_CONVERSANDO, dados)
                return resp

        # 5. Finalizar pedido
        if any(p in msg_lower for p in ['so isso', 'só isso', 'fechar', 'finalizar', 'nao quero mais', 'não quero mais', 'pronto', 'acabou']):
            if pedido_contexto:
                total = sum((i['preco'] + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)
                return f"Perfeito! Seu pedido ficou em R$ {total:.2f}. Vou precisar do seu endereço para entrega. Pode me passar? 📍"
            return "Você ainda não pediu nada! O que vai querer? 😊"

        # 5. Ver pedido atual
        if any(p in msg_lower for p in ['meu pedido', 'o que pedi', 'quanto ta', 'quanto tá', 'quanto deu', 'carrinho']):
            if pedido_contexto:
                total = sum((i['preco'] + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)
                resumo = "📋 *Seu pedido:*\n"
                for item in pedido_contexto:
                    preco_item = (item['preco'] + item.get('preco_adicionais', 0)) * item.get('quantidade', 1)
                    resumo += f"• {item.get('quantidade', 1)}x {item['nome']} - R$ {preco_item:.2f}\n"
                resumo += f"\n💰 *Total: R$ {total:.2f}*\n\nQuer mais alguma coisa?"
                return resumo
            return "Seu carrinho está vazio! O que vai querer? 😊"

        # 6. Perguntas genéricas - responde de forma útil
        if '?' in mensagem:
            return "Hmm, deixa eu te ajudar! Posso te mostrar nosso cardápio ou tirar dúvidas sobre algum produto específico. O que prefere? 😊"

        # 7. Fallback final - sempre útil, nunca erro
        if pedido_contexto:
            total = sum((i['preco'] + i.get('preco_adicionais', 0)) * i.get('quantidade', 1) for i in pedido_contexto)
            return f"Entendi! Você já tem R$ {total:.2f} no pedido. Quer adicionar mais alguma coisa ou posso fechar? 😊"

        return "Opa! Como posso te ajudar? Posso mostrar o cardápio, tirar dúvidas ou anotar seu pedido! 😊"

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
            removidos = item.get("removidos", [])
            adicionais = item.get("adicionais", [])  # Nomes para exibição
            complementos_checkout = item.get("complementos_checkout", [])  # IDs para o endpoint

            # Observação = APENAS os removidos (SEM: cebola, SEM: tomate)
            observacao = None
            if removidos:
                observacao = f"SEM: {', '.join(removidos)}"

            carrinho_item = {
                "id": item.get("id", ""),
                "nome": item["nome"],
                "preco": item["preco"],
                "quantidade": item.get("quantidade", 1),
                "observacoes": observacao,  # Só os removidos vão aqui
                "complementos": complementos_checkout,  # Estrutura com IDs para o endpoint
                "personalizacoes": {
                    "removidos": removidos,
                    "adicionais": adicionais,  # Nomes para exibição
                    "preco_adicionais": item.get("preco_adicionais", 0.0),
                    "complemento_obrigatorio": item.get("complemento_obrigatorio", False)
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
            'descricao': produto.get('descricao', ''),
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
        Funciona tanto com carrinho quanto com pedido_contexto (modo conversacional)

        Args:
            dados: Dados da conversa com carrinho ou pedido_contexto
            acao: 'remover_ingrediente' ou 'adicionar_extra'
            item_nome: Nome do ingrediente/adicional
            produto_busca: Nome do produto (opcional, usa último adicionado)

        Returns:
            (sucesso, mensagem)
        """
        carrinho = dados.get('carrinho', [])
        pedido_contexto = dados.get('pedido_contexto', [])
        
        # No modo conversacional, usa pedido_contexto se carrinho estiver vazio
        lista_itens = carrinho if carrinho else pedido_contexto
        usando_contexto = not carrinho and pedido_contexto

        if not lista_itens:
            return (False, "Seu carrinho está vazio! Primeiro adicione um produto 😊")

        # Encontra o produto na lista
        produto_alvo = None
        if produto_busca:
            # Busca pelo nome
            for item in lista_itens:
                item_nome_check = item.get('nome', '')
                if produto_busca.lower() in item_nome_check.lower():
                    produto_alvo = item
                    break
        else:
            # Usa o último adicionado
            produto_alvo = lista_itens[-1]

        if not produto_alvo:
            return (False, f"Não encontrei '{produto_busca}' no seu carrinho 🤔")

        # No modo conversacional, trabalha com pedido_contexto que tem estrutura diferente
        if usando_contexto:
            # Inicializa estruturas se não existirem
            if 'removidos' not in produto_alvo:
                produto_alvo['removidos'] = []
            if 'adicionais' not in produto_alvo:
                produto_alvo['adicionais'] = []
            if 'preco_adicionais' not in produto_alvo:
                produto_alvo['preco_adicionais'] = 0.0

            if acao == "remover_ingrediente":
                # Verifica se o ingrediente existe na receita
                ingrediente = self.ingredientes_service.verificar_ingrediente_na_receita_por_nome(
                    produto_alvo['nome'], item_nome
                )

                if ingrediente:
                    if ingrediente['nome'] not in produto_alvo['removidos']:
                        produto_alvo['removidos'].append(ingrediente['nome'])
                        dados['pedido_contexto'] = pedido_contexto
                        return (True, f"✅ Ok! *{produto_alvo['nome']}* SEM {ingrediente['nome']} 👍")
                    else:
                        return (True, f"Esse já tá sem {ingrediente['nome']}! 😊")
                else:
                    return (False, f"Hmm, {produto_alvo['nome']} não leva {item_nome} 🤔")

            elif acao == "adicionar_extra":
                # Busca o adicional
                adicional = self.ingredientes_service.buscar_adicional_por_nome(item_nome)

                if adicional:
                    # Verifica se já foi adicionado (compara nomes)
                    adicionais_nomes = [add if isinstance(add, str) else add.get('nome', '') for add in produto_alvo['adicionais']]
                    if adicional['nome'].lower() not in [a.lower() for a in adicionais_nomes]:
                        produto_alvo['adicionais'].append(adicional['nome'])
                        produto_alvo['preco_adicionais'] += adicional['preco']
                        dados['pedido_contexto'] = pedido_contexto
                        return (True, f"✅ Adicionei *{adicional['nome']}* (+R$ {adicional['preco']:.2f}) no seu *{produto_alvo['nome']}* 👍")
                    else:
                        return (True, f"Já adicionei {adicional['nome']}! 😊")
                else:
                    # Lista os adicionais disponíveis
                    todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
                    if todos_adicionais:
                        nomes = [a['nome'] for a in todos_adicionais[:5]]
                        return (False, f"Não encontrei esse adicional 🤔\n\nTemos disponível: {', '.join(nomes)}")
                    return (False, f"Não encontrei esse adicional 🤔")
            
            return (False, "Não entendi a personalização 😅")
        
        # Modo normal com carrinho (estrutura com personalizacoes)
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
                    "descricao": "",  # Produtos simples não têm descrição detalhada
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

    def _normalizar_termo_busca(self, termo: str) -> str:
        """
        Normaliza termo de busca removendo acentos, espaços extras e caracteres especiais.
        """
        def remover_acentos(texto: str) -> str:
            acentos = {
                'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
                'é': 'e', 'ê': 'e', 'ë': 'e',
                'í': 'i', 'î': 'i', 'ï': 'i',
                'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
                'ú': 'u', 'û': 'u', 'ü': 'u',
                'ç': 'c', 'ñ': 'n'
            }
            for acentuado, sem_acento in acentos.items():
                texto = texto.replace(acentuado, sem_acento)
                texto = texto.replace(acentuado.upper(), sem_acento.upper())
            return texto
        
        # Remove acentos e converte para minúsculas
        termo_normalizado = remover_acentos(termo.lower().strip())
        # Remove espaços extras e caracteres especiais (mantém apenas letras e números)
        termo_normalizado = re.sub(r'[^\w\s]', '', termo_normalizado)
        termo_normalizado = re.sub(r'\s+', ' ', termo_normalizado).strip()
        return termo_normalizado

    def _corrigir_termo_busca(self, termo: str, lista_referencia: List[str], threshold: float = 0.6) -> str:
        """
        Corrige erros de digitação usando difflib.
        Exemplo: "te hmburg" -> "hamburg"
        """
        if not termo or not lista_referencia:
            return termo
        
        termo_normalizado = self._normalizar_termo_busca(termo)
        
        # Tenta encontrar correspondência mais próxima
        matches = get_close_matches(
            termo_normalizado,
            [self._normalizar_termo_busca(ref) for ref in lista_referencia],
            n=1,
            cutoff=threshold
        )
        
        if matches:
            # Encontra o termo original correspondente
            for ref in lista_referencia:
                if self._normalizar_termo_busca(ref) == matches[0]:
                    print(f"🔧 Correção: '{termo}' -> '{ref}'")
                    return ref
        
        return termo

    def _expandir_sinonimos(self, termo: str) -> List[str]:
        """
        Expande termo com sinônimos e variações comuns.
        Exemplo: "hamburg" -> ["hamburg", "hamburger", "burger", "hamburguer"]
        """
        # Dicionário de sinônimos e variações comuns
        sinonimos = {
            'hamburg': ['hamburger', 'burger', 'hamburguer', 'hambúrguer'],
            'burger': ['hamburger', 'hamburg', 'hamburguer', 'hambúrguer'],
            'hamburger': ['hamburg', 'burger', 'hamburguer', 'hambúrguer'],
            'pizza': ['pizzas'],
            'refri': ['refrigerante', 'refris'],
            'refrigerante': ['refri', 'refris'],
            'coca': ['coca cola', 'cocacola'],
            'batata': ['batatas', 'fritas'],
            'batata frita': ['batatas fritas', 'fritas'],
            'x': ['x-', 'xis'],
            'xis': ['x-', 'x'],
        }
        
        termo_lower = termo.lower().strip()
        termos_expandidos = [termo]
        
        # Adiciona sinônimos se encontrar
        for chave, valores in sinonimos.items():
            if chave in termo_lower:
                termos_expandidos.extend(valores)
                # Substitui a chave pelos sinônimos no termo
                for valor in valores:
                    termo_substituido = termo_lower.replace(chave, valor)
                    if termo_substituido != termo_lower:
                        termos_expandidos.append(termo_substituido)
        
        # Remove duplicatas mantendo ordem
        termos_unicos = []
        for t in termos_expandidos:
            if t not in termos_unicos:
                termos_unicos.append(t)
        
        return termos_unicos[:5]  # Limita a 5 variações para não sobrecarregar

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
        if not termo_busca or len(termo_busca.strip()) < 2:
            return []
        
        try:
            from sqlalchemy import text
            
            termo_original = termo_busca.strip()
            termo_normalizado = self._normalizar_termo_busca(termo_original)
            
            # Expande com sinônimos
            termos_busca = self._expandir_sinonimos(termo_original)
            termos_busca.append(termo_normalizado)  # Adiciona versão normalizada
            
            # Remove duplicatas
            termos_busca = list(dict.fromkeys(termos_busca))[:3]  # Limita a 3 termos para performance
            
            resultados = []
            
            # Busca em produtos
            for termo in termos_busca:
                termo_sql = f"%{termo}%"
                query_produtos = text("""
                    SELECT p.cod_barras, p.descricao, pe.preco_venda, 'produto' as tipo
                    FROM catalogo.produtos p
                    JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                    WHERE pe.empresa_id = :empresa_id
                    AND p.ativo = true
                    AND pe.disponivel = true
                    AND (
                        LOWER(REPLACE(REPLACE(p.descricao, '-', ''), ' ', '')) LIKE LOWER(REPLACE(REPLACE(:termo, '-', ''), ' ', ''))
                        OR LOWER(p.descricao) LIKE LOWER(:termo)
                    )
                    ORDER BY 
                        CASE 
                            WHEN LOWER(p.descricao) = LOWER(:termo_exato) THEN 1
                            WHEN LOWER(p.descricao) LIKE LOWER(:termo_inicio) THEN 2
                            ELSE 3
                        END,
                        p.descricao
                    LIMIT :limit
                """)
                
                result = self.db.execute(query_produtos, {
                    "empresa_id": self.empresa_id,
                    "termo": termo_sql,
                    "termo_exato": termo,
                    "termo_inicio": f"{termo}%",
                    "limit": limit
                })
                
                for row in result.fetchall():
                    produto = {
                        "id": row[0],
                        "nome": row[1],
                        "preco": float(row[2]),
                        "tipo": row[3]
                    }
                    # Evita duplicatas
                    if not any(r.get("id") == produto["id"] and r.get("tipo") == produto["tipo"] for r in resultados):
                        resultados.append(produto)
                
                if len(resultados) >= limit:
                    break
            
            # Se ainda não encontrou o suficiente, busca em receitas
            if len(resultados) < limit:
                for termo in termos_busca:
                    termo_sql = f"%{termo}%"
                    query_receitas = text("""
                        SELECT id, nome, preco_venda, 'receita' as tipo
                        FROM catalogo.receitas
                        WHERE empresa_id = :empresa_id
                        AND ativo = true
                        AND disponivel = true
                        AND (
                            LOWER(REPLACE(REPLACE(nome, '-', ''), ' ', '')) LIKE LOWER(REPLACE(REPLACE(:termo, '-', ''), ' ', ''))
                            OR LOWER(nome) LIKE LOWER(:termo)
                            OR (descricao IS NOT NULL AND LOWER(descricao) LIKE LOWER(:termo))
                        )
                        ORDER BY 
                            CASE 
                                WHEN LOWER(nome) = LOWER(:termo_exato) THEN 1
                                WHEN LOWER(nome) LIKE LOWER(:termo_inicio) THEN 2
                                ELSE 3
                            END,
                            nome
                        LIMIT :limit
                    """)
                    
                    result = self.db.execute(query_receitas, {
                        "empresa_id": self.empresa_id,
                        "termo": termo_sql,
                        "termo_exato": termo,
                        "termo_inicio": f"{termo}%",
                        "limit": limit - len(resultados)
                    })
                    
                    for row in result.fetchall():
                        receita = {
                            "id": f"receita_{row[0]}",
                            "nome": row[1],
                            "preco": float(row[2]) if row[2] else 0.0,
                            "tipo": row[3]
                        }
                        # Evita duplicatas
                        if not any(r.get("id") == receita["id"] and r.get("tipo") == receita["tipo"] for r in resultados):
                            resultados.append(receita)
                    
                    if len(resultados) >= limit:
                        break
            
            # Se ainda não encontrou o suficiente, busca em combos
            if len(resultados) < limit:
                for termo in termos_busca:
                    termo_sql = f"%{termo}%"
                    query_combos = text("""
                        SELECT id, titulo, preco_total, 'combo' as tipo
                        FROM catalogo.combos
                        WHERE empresa_id = :empresa_id
                        AND ativo = true
                        AND (
                            (titulo IS NOT NULL AND (
                                LOWER(REPLACE(REPLACE(titulo, '-', ''), ' ', '')) LIKE LOWER(REPLACE(REPLACE(:termo, '-', ''), ' ', ''))
                                OR LOWER(titulo) LIKE LOWER(:termo)
                            ))
                            OR LOWER(descricao) LIKE LOWER(:termo)
                        )
                        ORDER BY 
                            CASE 
                                WHEN titulo IS NOT NULL AND LOWER(titulo) = LOWER(:termo_exato) THEN 1
                                WHEN titulo IS NOT NULL AND LOWER(titulo) LIKE LOWER(:termo_inicio) THEN 2
                                ELSE 3
                            END,
                            titulo
                        LIMIT :limit
                    """)
                    
                    result = self.db.execute(query_combos, {
                        "empresa_id": self.empresa_id,
                        "termo": termo_sql,
                        "termo_exato": termo,
                        "termo_inicio": f"{termo}%",
                        "limit": limit - len(resultados)
                    })
                    
                    for row in result.fetchall():
                        combo = {
                            "id": f"combo_{row[0]}",
                            "nome": row[1] or f"Combo {row[0]}",
                            "preco": float(row[2]) if row[2] else 0.0,
                            "tipo": row[3]
                        }
                        # Evita duplicatas
                        if not any(r.get("id") == combo["id"] and r.get("tipo") == combo["tipo"] for r in resultados):
                            resultados.append(combo)
                    
                    if len(resultados) >= limit:
                        break
            
            # Se não encontrou nada, tenta correção de erros usando lista de referência
            if not resultados:
                # Busca lista de referência (primeiros 100 nomes de produtos/receitas/combos)
                query_referencia = text("""
                    (
                        SELECT descricao as nome FROM catalogo.produtos p
                        JOIN catalogo.produtos_empresa pe ON p.cod_barras = pe.cod_barras
                        WHERE pe.empresa_id = :empresa_id AND p.ativo = true AND pe.disponivel = true
                        LIMIT 50
                    )
                    UNION
                    (
                        SELECT nome FROM catalogo.receitas
                        WHERE empresa_id = :empresa_id AND ativo = true AND disponivel = true
                        LIMIT 30
                    )
                    UNION
                    (
                        SELECT COALESCE(titulo, descricao) as nome FROM catalogo.combos
                        WHERE empresa_id = :empresa_id AND ativo = true
                        LIMIT 20
                    )
                """)
                
                result_ref = self.db.execute(query_referencia, {"empresa_id": self.empresa_id})
                lista_referencia = [row[0] for row in result_ref.fetchall()]
                
                # Tenta corrigir o termo
                termo_corrigido = self._corrigir_termo_busca(termo_original, lista_referencia)
                
                # Se corrigiu, busca novamente
                if termo_corrigido != termo_original:
                    return self._buscar_produtos_inteligente(termo_corrigido, limit)
            
            return resultados[:limit]  # Garante que não retorna mais que o limite
            
        except Exception as e:
            print(f"❌ Erro ao buscar produtos inteligente: {e}")
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

            # Ir para pagamento (ou resumo se já foi detectado)
            return await self._ir_para_pagamento_ou_resumo(
                user_id, dados,
                f"✅ Endereço selecionado:\n📍 {endereco_selecionado['endereco_completo']}\n\n"
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
        return await self._ir_para_pagamento_ou_resumo(
            user_id, dados,
            f"✅ Endereço salvo!\n📍 {endereco_completo}\n\n"
        )

    def _mensagem_formas_pagamento(self) -> str:
        """Retorna a mensagem de formas de pagamento baseada no banco de dados"""
        meios = self._buscar_meios_pagamento()

        # Emojis por tipo de pagamento
        emoji_por_tipo = {
            'PIX_ENTREGA': '📱',
            'PIX_ONLINE': '📱',
            'DINHEIRO': '💵',
            'CARTAO_ENTREGA': '💳',
            'OUTROS': '💰'
        }

        # Números em emoji
        numeros_emoji = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        mensagem = "Agora me fala, como vai ser o pagamento?\n\n💳 *Formas disponíveis:*\n"

        for i, meio in enumerate(meios):
            emoji_num = numeros_emoji[i] if i < len(numeros_emoji) else f"{i+1}."
            emoji_tipo = emoji_por_tipo.get(meio.get('tipo', 'OUTROS'), '💰')
            mensagem += f"{emoji_num} {emoji_tipo} {meio['nome']}\n"

        mensagem += "\nDigite o número da opção ou a forma de pagamento!"
        return mensagem

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

            print("🏪 Cliente escolheu RETIRADA, indo para pagamento")
            return await self._ir_para_pagamento_ou_resumo(
                user_id, dados,
                "Beleza! Você vai retirar aqui na loja 🏪\n\n"
            )

        else:
            # Não entendeu
            return "Não entendi 😅\nDigite *1* pra entrega ou *2* pra retirada na loja"

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

        return f"Ops! Escolhe uma das opções:\n{opcoes_str}\n\nOu digite diretamente: {nomes_str} 😊"

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

        # Montar mensagem
        mensagem = "📋 *RESUMO DO PEDIDO*\n\n"
        mensagem += "*Itens:*\n"
        for item in carrinho:
            qtd = item.get('quantidade', 1)
            preco_adicionais = item.get('personalizacoes', {}).get('preco_adicionais', 0.0)
            subtotal_item = (item['preco'] + preco_adicionais) * qtd
            mensagem += f"• {qtd}x {item['nome']} - R$ {subtotal_item:.2f}\n"
            # Mostra adicionais se tiver
            adicionais = item.get('personalizacoes', {}).get('adicionais', [])
            if adicionais:
                mensagem += f"  _Complemento: {', '.join(adicionais)}_\n"
            # Mostra removidos se tiver
            removidos = item.get('personalizacoes', {}).get('removidos', [])
            if removidos:
                mensagem += f"  _Sem: {', '.join(removidos)}_\n"

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
                observacao = item.get('observacoes')  # Só os "SEM:" vão aqui
                complementos = item.get('complementos', [])  # Estrutura com IDs

                # Se o ID começa com "receita_", é uma receita
                if isinstance(item_id, str) and item_id.startswith('receita_'):
                    receita_id = int(item_id.replace('receita_', ''))
                    receita_item = {
                        "receita_id": receita_id,
                        "quantidade": quantidade,
                        "observacao": observacao
                    }
                    # Adiciona complementos se tiver
                    if complementos:
                        receita_item["complementos"] = complementos
                    receitas_checkout.append(receita_item)
                else:
                    # É um produto com código de barras
                    produto_item = {
                        "produto_cod_barras": item_id,
                        "quantidade": quantidade,
                        "observacao": observacao
                    }
                    # Adiciona complementos se tiver
                    if complementos:
                        produto_item["complementos"] = complementos
                    itens_checkout.append(produto_item)

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

            # Adiciona meio de pagamento se foi detectado
            meio_pagamento_id = dados.get('meio_pagamento_id')
            if meio_pagamento_id:
                # Calcula o total do pedido para o valor do pagamento
                total = sum(
                    (item.get('preco', 0) + item.get('personalizacoes', {}).get('preco_adicionais', 0))
                    * item.get('quantidade', 1)
                    for item in carrinho
                )
                # Adiciona taxa de entrega se for delivery
                if tipo_entrega == 'ENTREGA':
                    total += 5.00  # TODO: calcular taxa real baseada na distância

                payload["meios_pagamento"] = [{
                    "id": meio_pagamento_id,
                    "valor": total
                }]
                print(f"[Checkout] Meio de pagamento: {forma_pagamento} (ID: {meio_pagamento_id}), Valor: R$ {total:.2f}")

            print(f"[Checkout] Payload: {json.dumps(payload, indent=2)}")

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
        try:
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
            else:
                # Se não encontrou ingredientes, retorna mensagem básica
                msg = f"*{produto['nome']}* - R$ {produto['preco']:.2f}\n\n"
                if produto.get('descricao'):
                    msg += f"{produto['descricao']}\n\n"
                msg += "Quer adicionar ao pedido? 😊"
                return msg
        except Exception as e:
            print(f"❌ Erro ao buscar ingredientes de {produto.get('nome', 'produto')}: {e}")
            # Fallback básico
            msg = f"*{produto['nome']}* - R$ {produto['preco']:.2f}\n\n"
            msg += "Quer adicionar ao pedido? 😊"
            return msg

    # ========== PROCESSAMENTO PRINCIPAL ==========

    async def processar_mensagem(self, user_id: str, mensagem: str) -> str:
        """
        Processa mensagem usando Groq API com fluxo de endereços integrado
        """
        try:
            # Obtém estado atual
            estado, dados = self._obter_estado_conversa(user_id)
            print(f"📊 Estado atual: {estado}")

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

            # Se for primeira mensagem (saudação), entra no modo conversacional
            if self._eh_primeira_mensagem(mensagem):
                dados['historico'] = [{"role": "user", "content": mensagem}]
                dados['carrinho'] = []
                dados['pedido_contexto'] = []  # Lista de itens mencionados na conversa
                dados['produtos_encontrados'] = self._buscar_promocoes()
                # LIMPA pagamento de conversa anterior
                dados['forma_pagamento'] = None
                dados['meio_pagamento_id'] = None
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

                    # Monta mensagem de confirmação
                    import random
                    msg_resposta = f"✅ *{quantidade}x {produto['nome']}* adicionado!\n"

                    # Busca ingredientes para mostrar descrição do produto
                    ingredientes = self.ingredientes_service.buscar_ingredientes_por_nome_receita(produto['nome'])
                    if ingredientes:
                        ing_lista = [i['nome'] for i in ingredientes[:5]]  # Máximo 5 ingredientes
                        msg_resposta += f"📋 _{', '.join(ing_lista)}_\n"

                    msg_resposta += f"\n💰 Total: R$ {total:.2f}"

                    # Busca complementos disponíveis para o produto
                    complementos = self.ingredientes_service.buscar_complementos_por_nome_receita(produto['nome'])

                    if complementos:
                        tem_obrigatorio = self.ingredientes_service.tem_complementos_obrigatorios(complementos)

                        if tem_obrigatorio:
                            # Se tem complemento obrigatório, mostra e pede para escolher
                            msg_resposta += self.ingredientes_service.formatar_complementos_para_chat(complementos, produto['nome'])
                            msg_resposta += "\n\n_Escolha os complementos obrigatórios para continuar!_"
                        else:
                            # Se não for obrigatório, mostra os complementos direto
                            msg_resposta += self.ingredientes_service.formatar_complementos_para_chat(complementos, produto['nome'])
                            msg_resposta += "\n\n_Digite o que deseja adicionar ou continue seu pedido!_ 😊"
                            dados['aguardando_complemento'] = True

                        # Salva produto atual para referência dos complementos
                        dados['ultimo_produto_adicionado'] = produto['nome']
                        dados['complementos_disponiveis'] = complementos
                        self._salvar_estado_conversa(user_id, STATE_AGUARDANDO_PEDIDO, dados)
                    else:
                        msg_resposta += "\n\nMais alguma coisa? 😊"

                    return msg_resposta
                else:
                    # Verifica se parece ser uma intenção genérica de pedir (não um produto específico)
                    termos_genericos = ['fazer', 'pedido', 'pedir', 'quero um', 'quero uma', 'algo', 'alguma coisa']
                    if any(t in produto_busca.lower() for t in termos_genericos):
                        return "Claro! O que você gostaria de pedir? Posso te mostrar o cardápio se quiser! 😊"
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
            return self._fallback_resposta_inteligente(mensagem, dados)

        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            import traceback
            traceback.print_exc()
            # Fallback inteligente - nunca retorna erro
            return self._fallback_resposta_inteligente(mensagem, dados)


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
    handler = GroqSalesHandler(db, empresa_id)
    resposta = await handler.processar_mensagem(user_id, mensagem)

    # 4. Salva resposta do bot no banco
    assistant_message_id = chatbot_db.create_message(db, conversation_id, "assistant", resposta)
    
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

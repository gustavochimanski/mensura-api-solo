"""
Agentes especializados para detecção de intenções do chatbot.
Cada agente é responsável por uma categoria específica de intenções.
"""
import re
from typing import Dict, Any, Optional, List
from enum import Enum


class IntentionType(Enum):
    """Tipos de intenções que podem ser detectadas"""
    INICIAR_PEDIDO = "iniciar_pedido"
    ADICIONAR_PRODUTO = "adicionar_produto"
    VER_CARDAPIO = "ver_cardapio"
    VER_CARRINHO = "ver_carrinho"
    FINALIZAR_PEDIDO = "finalizar_pedido"
    REMOVER_PRODUTO = "remover_produto"
    INFORMAR_PRODUTO = "informar_produto"
    PERSONALIZAR_PRODUTO = "personalizar_produto"
    VER_ADICIONAIS = "ver_adicionais"
    VER_COMBOS = "ver_combos"
    CALCULAR_TAXA_ENTREGA = "calcular_taxa_entrega"
    CHAMAR_ATENDENTE = "chamar_atendente"
    CONVERSAR = "conversar"
    DESCONHECIDA = "desconhecida"


class IntentionAgent:
    """Agente base para detecção de intenções"""
    
    def __init__(self, priority: int = 0):
        """
        Args:
            priority: Prioridade do agente (maior = verificado primeiro)
        """
        self.priority = priority
    
    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta se a mensagem corresponde à intenção deste agente.
        
        Args:
            mensagem: Mensagem original
            mensagem_normalizada: Mensagem normalizada (lowercase, sem acentos, etc)
            context: Contexto adicional (carrinho, produtos, etc)
        
        Returns:
            Dict com 'intention', 'funcao' e 'params' se detectar, None caso contrário
        """
        raise NotImplementedError


class IniciarPedidoAgent(IntentionAgent):
    """Agente especializado em detectar intenção de INICIAR um novo pedido"""
    
    def __init__(self):
        super().__init__(priority=100)  # Alta prioridade - deve ser verificado ANTES de adicionar produto
    
    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta intenção de iniciar novo pedido.
        IMPORTANTE: NÃO deve detectar quando há produto específico mencionado.
        """
        # Padrões que indicam iniciar pedido (SEM produto específico)
        padroes_iniciar = [
            # "gostaria de fazer um pedido", "gostaria de fazer pedido"
            r'(?:gostaria|gostaria de|queria|queria de)\s+(?:fazer|fazer um|fazer uma)\s+(?:pedido|novo\s+pedido)',
            # "fazer novo pedido", "fazer pedido"
            r'fazer\s+(?:novo\s+)?pedido(?!\s+de\s+\w)',  # NÃO "fazer pedido de pizza"
            # "novo pedido"
            r'novo\s+pedido',
            # "começar de novo", "comecar de novo"
            r'come[cç]ar\s+(?:de\s+)?novo',
            # "iniciar pedido", "iniciar novo pedido"
            r'iniciar\s+(?:novo\s+)?pedido',
            # "quero fazer pedido" (mas NÃO "quero fazer pedido de pizza")
            r'quero\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            # "quero pedir" (mas NÃO "quero pedir pizza")
            r'quero\s+pedir(?!\s+\w)',
            # "vou fazer pedido", "vou pedir"
            r'vou\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'vou\s+pedir(?!\s+\w)',
            # "preciso fazer pedido", "preciso pedir"
            r'preciso\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'preciso\s+pedir(?!\s+\w)',
            # "fazer um pedido" (genérico)
            r'fazer\s+um\s+pedido(?!\s+de\s+\w)',
        ]
        
        # Verifica se menciona produto específico (ex: "fazer pedido de pizza")
        tem_produto_especifico = re.search(
            r'(?:fazer|fazer um|pedir|quero fazer|vou fazer)\s+(?:pedido|um pedido)\s+de\s+(\w+)',
            mensagem_normalizada,
            re.IGNORECASE
        )
        
        # Se tem produto específico, NÃO é iniciar pedido, é adicionar produto
        if tem_produto_especifico:
            return None
        
        # Verifica cada padrão
        for padrao in padroes_iniciar:
            if re.search(padrao, mensagem_normalizada, re.IGNORECASE):
                print(f"🆕 [Agente IniciarPedido] Detectado: '{mensagem}'")
                return {
                    "intention": IntentionType.INICIAR_PEDIDO,
                    "funcao": "iniciar_novo_pedido",
                    "params": {}
                }
        
        return None


class AdicionarProdutoAgent(IntentionAgent):
    """Agente especializado em detectar intenção de ADICIONAR produto ao carrinho"""
    
    def __init__(self):
        super().__init__(priority=50)  # Prioridade média - verificado depois de iniciar pedido
    
    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta intenção de adicionar produto.
        IMPORTANTE: Só detecta se houver MENÇÃO CLARA de produto.
        """
        # PRIMEIRO: Verifica se NÃO é uma intenção de iniciar pedido genérico
        # Ex: "gostaria de fazer um pedido" não deve ser capturado como produto "pedido"
        padroes_iniciar_pedido = [
            r'(?:gostaria|gostaria de|queria|queria de)\s+(?:fazer|fazer um|fazer uma)\s+(?:pedido|novo\s+pedido)',
            r'fazer\s+(?:novo\s+)?pedido(?!\s+de\s+\w)',
            r'novo\s+pedido',
            r'quero\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'quero\s+pedir(?!\s+\w)',
            r'vou\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'preciso\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
        ]
        
        # Se corresponde a iniciar pedido genérico, NÃO é adicionar produto
        for padrao in padroes_iniciar_pedido:
            if re.search(padrao, mensagem_normalizada, re.IGNORECASE):
                return None  # Deixa o IniciarPedidoAgent lidar com isso
        
        # Padrões que indicam adicionar produto (com produto mencionado)
        patterns_pedido = [
            # "quero X", "quero um X", "quero 2 X"
            (r'(?:quero|qro)\s+(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+)\s*)?(.+)', 1, 2),
            # "me ve X", "me vê X", "manda X", "traz X"
            (r'(?:me\s+)?(?:ve|vê|manda|traz)\s+(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+)\s*)?(.+)', 1, 2),
            # "2 X", "um X", "duas X"
            (r'(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+))\s+(.+?)(?:\s+por\s+favor)?$', 1, 2),
            # "pode ser X", "vou querer X"
            (r'(?:pode\s+ser|vou\s+querer)\s+(?:(uma?|um|duas?|dois|doise|tres|tr[eê]s|\d+)\s*)?(.+)', 1, 2),
            # "fazer pedido de X", "quero fazer pedido de X"
            (r'(?:fazer|quero fazer|vou fazer)\s+(?:pedido|um pedido)\s+de\s+(.+)', None, 1),
        ]
        
        def _parse_quantidade_token(token: Optional[str]) -> int:
            if not token:
                return 1
            t = mensagem_normalizada if isinstance(token, str) else str(token)
            if t.isdigit():
                return max(int(t), 1)
            mapa = {
                "um": 1, "uma": 1, "dois": 2, "duas": 2, "doise": 2,
                "tres": 3, "três": 3, "quatro": 4, "cinco": 5,
                "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
            }
            return mapa.get(t, 1)
        
        def _limpar_termos_finais(texto: str) -> str:
            """Remove termos como 'então', 'aí', 'por favor' do final"""
            t = texto.strip()
            stop_finais = ["entao", "então", "ai", "aí", "pf", "pfv", "por favor", "ok", "blz"]
            while True:
                t_norm = t.lower().strip()
                if not t_norm:
                    return ""
                tokens = t_norm.split()
                if not tokens:
                    return ""
                if t_norm.endswith("por favor"):
                    t = re.sub(r"\s*por\s+favor\s*$", "", t, flags=re.IGNORECASE).strip()
                    continue
                last = tokens[-1]
                if last in stop_finais:
                    t = re.sub(rf"\s*{re.escape(last)}\s*$", "", t, flags=re.IGNORECASE).strip()
                    continue
                return t.strip()
        
        # Verifica cada padrão
        for pattern, qtd_group, produto_group in patterns_pedido:
            match = re.search(pattern, mensagem_normalizada)
            if match:
                qtd_token = (match.group(qtd_group) or "").strip() if qtd_group and match.lastindex and match.lastindex >= qtd_group else ""
                produto_completo = (match.group(produto_group) or "").strip() if match.lastindex and match.lastindex >= produto_group else ""
                
                if not produto_completo or len(produto_completo) < 2:
                    continue
                
                # Parse quantidade
                quantidade = _parse_quantidade_token(qtd_token)
                
                # Verifica quantidade dentro do produto (ex: "2x bacon")
                qtd_match = re.search(r'^(\d+)\s*x?\s*', produto_completo)
                if qtd_match:
                    quantidade = max(int(qtd_match.group(1)), 1)
                    produto_completo = produto_completo[qtd_match.end():].strip()
                
                # Remove personalização do nome do produto
                produto_limpo = produto_completo
                personalizacao = None
                
                # Detecta "sem X"
                match_sem = re.search(r'\s+sem\s+(\w+)', produto_completo, re.IGNORECASE)
                if match_sem:
                    personalizacao = {"acao": "remover_ingrediente", "item": match_sem.group(1)}
                    produto_limpo = re.sub(r'\s+sem\s+\w+', '', produto_completo, flags=re.IGNORECASE).strip()
                
                # Detecta "com X extra" ou "mais X"
                match_extra = re.search(r'\s+(?:com|mais|extra)\s+(\w+)', produto_completo, re.IGNORECASE)
                if match_extra and not personalizacao:
                    personalizacao = {"acao": "adicionar_extra", "item": match_extra.group(1)}
                    produto_limpo = re.sub(r'\s+(?:com|mais|extra)\s+\w+', '', produto_completo, flags=re.IGNORECASE).strip()
                
                produto_limpo = _limpar_termos_finais(produto_limpo)
                
                # Se ficou muito curto, pode ser que não seja produto
                if not produto_limpo or len(produto_limpo) < 2:
                    continue
                
                # Verifica se não é uma frase genérica de iniciar pedido
                palavras_genericas = ['pedido', 'pedir', 'fazer', 'novo', 'um', 'uma']
                if produto_limpo.lower() in palavras_genericas:
                    continue
                
                # Verifica se a mensagem completa é sobre iniciar pedido (não adicionar produto)
                # Ex: "gostaria de fazer um pedido" não deve ser capturado como produto "pedido"
                if re.search(r'(?:gostaria|queria|quero|vou|preciso)\s+(?:de\s+)?(?:fazer|fazer um|fazer uma)\s+(?:pedido|novo\s+pedido)(?!\s+de\s+\w)', mensagem_normalizada, re.IGNORECASE):
                    # Se a mensagem é sobre iniciar pedido genérico, não é adicionar produto
                    continue
                
                print(f"🛒 [Agente AdicionarProduto] Detectado: '{mensagem}' -> produto: '{produto_limpo}', qtd: {quantidade}")
                
                params = {"produto_busca": produto_limpo, "quantidade": max(int(quantidade), 1)}
                if personalizacao:
                    params["personalizacao"] = personalizacao
                
                return {
                    "intention": IntentionType.ADICIONAR_PRODUTO,
                    "funcao": "adicionar_produto",
                    "params": params
                }
        
        return None


class ConversacaoAgent(IntentionAgent):
    """Agente especializado em detectar saudações e conversas casuais"""
    
    def __init__(self):
        super().__init__(priority=10)  # Baixa prioridade - fallback
    
    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Detecta saudações e conversas casuais"""
        # Saudações
        if re.match(r'^(oi|ola|olá|eae|e ai|eaí|bom dia|boa tarde|boa noite|hey|hi)[\s!?]*$', mensagem_normalizada):
            return {
                "intention": IntentionType.CONVERSAR,
                "funcao": "conversar",
                "params": {"tipo_conversa": "saudacao"}
            }
        
        # Perguntas vagas
        if re.search(r'(o\s*que\s*(mais\s*)?(tem|vende)|que\s*que\s*é\s*bom|que\s*que\s*tem|não\s*sei|hum|talvez)', mensagem_normalizada):
            return {
                "intention": IntentionType.CONVERSAR,
                "funcao": "conversar",
                "params": {"tipo_conversa": "pergunta_vaga"}
            }
        
        return None


class IntentionRouter:
    """Roteador que coordena todos os agentes de intenção"""
    
    def __init__(self):
        # Lista de agentes ordenada por prioridade (maior primeiro)
        self.agents: List[IntentionAgent] = [
            IniciarPedidoAgent(),      # Prioridade 100 - verificado primeiro
            AdicionarProdutoAgent(),  # Prioridade 50
            ConversacaoAgent(),        # Prioridade 10 - fallback
        ]
        # Ordena por prioridade (maior primeiro)
        self.agents.sort(key=lambda a: a.priority, reverse=True)
    
    def detect_intention(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta a intenção da mensagem usando todos os agentes.
        
        Args:
            mensagem: Mensagem original
            mensagem_normalizada: Mensagem normalizada
            context: Contexto adicional
        
        Returns:
            Dict com 'intention', 'funcao' e 'params' se detectar, None caso contrário
        """
        # Tenta cada agente na ordem de prioridade
        for agent in self.agents:
            result = agent.detect(mensagem, mensagem_normalizada, context)
            if result:
                return result
        
        # Nenhum agente detectou
        return None

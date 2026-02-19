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
    ACOMPANHAR_PEDIDO = "acompanhar_pedido"
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
        Fluxo de pedido via chatbot foi desativado.
        Qualquer tentativa de 'iniciar pedido' deve redirecionar o usuário para ver o cardápio.
        """
        # Se detectar termos que indicam intenção de iniciar pedido, retornar intenção de ver cardápio
        padroes_iniciar = [
            r'(?:gostaria|gostaria de|queria|queria de)\s+(?:fazer|fazer um|fazer uma)\s+(?:pedido|novo\s+pedido)',
            r'fazer\s+(?:novo\s+)?pedido(?!\s+de\s+\w)',
            r'novo\s+pedido',
            r'come[cç]ar\s+(?:de\s+)?novo',
            r'iniciar\s+(?:novo\s+)?pedido',
            r'quero\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'quero\s+pedir(?!\s+\w)',
            r'vou\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'vou\s+pedir(?!\s+\w)',
            r'preciso\s+fazer\s+(?:um\s+)?pedido(?!\s+de\s+\w)',
            r'preciso\s+pedir(?!\s+\w)',
            r'fazer\s+um\s+pedido(?!\s+de\s+\w)',
        ]

        for padrao in padroes_iniciar:
            if re.search(padrao, mensagem_normalizada or "", re.IGNORECASE):
                print(f"➡️ [Agente IniciarPedido] Redirecionando para cardápio: '{mensagem}'")
                return {
                    "intention": IntentionType.VER_CARDAPIO,
                    "funcao": "ver_cardapio",
                    "params": {}
                }

        return None


class AcompanharPedidoAgent(IntentionAgent):
    """Agente para detectar intenção de acompanhar pedido do cliente"""

    def __init__(self):
        # Prioridade entre ver_cardapio (150) e iniciar_pedido (100)
        super().__init__(priority=120)

    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta frases como:
        - "gostaria de acompanhar meu pedido"
        - "queria acompanhar meu pedido por aqui"
        - "acompanhar pedido"
        """
        # Acompanhamento de pedidos depende de haver pedidos; como fluxo de pedido foi desativado,
        # redirecionamos para ver o cardápio caso o usuário tente acompanhar.
        if not mensagem_normalizada:
            return None
        padrao = r'(?:gostaria\s+de\s+|queria\s+|por\s+favor\s+)?acompanhar\s+(?:meu\s+)?pedido(?:\s+por\s+aqui)?'
        padrao_receber_atualizacoes = r'(?:gostaria\s+de\s+|queria\s+|por\s+favor\s+)?(?:receber|querer\s+receber)\s+.*atualiz'

        if re.search(padrao, mensagem_normalizada, re.IGNORECASE) or re.search(padrao_receber_atualizacoes, mensagem_normalizada, re.IGNORECASE):
            print(f"➡️ [Agente AcompanharPedido] Redirecionando para cardápio: '{mensagem}'")
            return {
                "intention": IntentionType.VER_CARDAPIO,
                "funcao": "ver_cardapio",
                "params": {}
            }
        return None


class ChamarAtendenteAgent(IntentionAgent):
    """Agente especializado em detectar intenção de CHAMAR ATENDENTE humano"""

    def __init__(self):
        # Prioridade muito alta: deve vir antes de cardápio e iniciar pedido
        super().__init__(priority=200)

    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta intenção de chamar atendente humano.

        IMPORTANTE:
        - Deve ser avaliado antes de detecções genéricas como "quero ..." (pedido),
          pois o cliente pode dizer "quero falar com um atendente".
        """
        msg = (mensagem_normalizada or "").strip()
        if not msg:
            return None

        # Suporta casos em que o frontend/WhatsApp envia o ID do botão como texto
        if msg == "chamar_atendente" or "chamar_atendente" in msg:
            return {
                "intention": IntentionType.CHAMAR_ATENDENTE,
                "funcao": "chamar_atendente",
                "params": {},
            }

        padrao = (
            r"(chamar\s+atendente|"
            r"quero\s+falar\s+com\s+(algu[eé]m|atendente|humano)|"
            r"preciso\s+de\s+(um\s+)?(humano|atendente)|"
            r"atendente\s+humano|"
            r"quero\s+atendimento\s+humano|"
            r"falar\s+com\s+atendente|"
            r"ligar\s+atendente|"
            r"chama\s+(algu[eé]m|atendente)\s+para\s+mi)"
        )
        if re.search(padrao, msg, re.IGNORECASE):
            print(f"📞 [Agente ChamarAtendente] Detectado: '{mensagem}'")
            return {
                "intention": IntentionType.CHAMAR_ATENDENTE,
                "funcao": "chamar_atendente",
                "params": {},
            }
        return None


class AdicionarProdutoAgent(IntentionAgent):
    """Agente especializado em detectar intenção de ADICIONAR produto ao carrinho"""
    
    def __init__(self):
        super().__init__(priority=50)  # Prioridade média - verificado depois de iniciar pedido
    
    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecção de intenção de adicionar produto foi desativada.
        Quando o usuário menciona um produto, o sistema deve apenas fornecer informações
        sobre o produto ou redirecionar para o cardápio (dependendo do fluxo principal).
        """
        # Não captura intenção de adicionar produto para prevenir fluxo de pedido via chatbot.
        return None


class VerCardapioAgent(IntentionAgent):
    """Agente especializado em detectar intenção de VER o cardápio"""
    
    def __init__(self):
        super().__init__(priority=150)  # Prioridade MUITO ALTA - verificado ANTES de iniciar pedido e cadastro
    
    def detect(self, mensagem: str, mensagem_normalizada: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Detecta intenção de ver o cardápio.
        Exemplos: "pode me mandar o cardápio", "quero ver o cardápio", "me manda o cardápio", etc.
        """
        # Padrões que indicam pedido de cardápio
        padroes_cardapio = [
            # "pode me mandar o cardápio", "poderia me mandar o cardápio"
            r'(?:pode|poderia)(?:\s+me)?\s+(?:me\s+)?(?:mandar|manda|enviar|envia|mostrar|mostra|passar|passa)\s+(?:o\s+)?(?:cardapio|cardápio|menu)',
            # "quero ver o cardápio", "gostaria de ver o cardápio"
            r'(?:quero|gostaria|gostaria de|queria|queria de)\s+(?:ver|ver o|receber|receber o|ter|ter o)\s+(?:cardapio|cardápio|menu)',
            # "me manda o cardápio", "manda o cardápio"
            r'(?:me\s+)?(?:manda|mandar|envia|enviar|mostra|mostrar|passa|passar)\s+(?:o\s+)?(?:cardapio|cardápio|menu)',
            # "manda aí o cardápio", "envia pra mim o cardápio"
            r'(?:manda|mandar|envia|enviar|mostra|mostrar|passa|passar)\s+(?:ai|aí|pra mim|para mim)\s+(?:o\s+)?(?:cardapio|cardápio|menu)',
            # Apenas "cardápio" ou "menu"
            r'^(?:cardapio|cardápio|menu)$',
            # "mostra o cardápio", "ver o cardápio"
            r'^(?:mostra|mostrar|ver|quero ver)\s+(?:o\s+)?(?:cardapio|cardápio|menu)$',
        ]
        
        for padrao in padroes_cardapio:
            if re.search(padrao, mensagem_normalizada, re.IGNORECASE):
                print(f"📋 [Agente VerCardapio] Detectado: '{mensagem}'")
                return {
                    "intention": IntentionType.VER_CARDAPIO,
                    "funcao": "ver_cardapio",
                    "params": {}
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
            ChamarAtendenteAgent(),    # Prioridade 200 - deve ser o PRIMEIRO
            VerCardapioAgent(),        # Prioridade 150 - verificado PRIMEIRO (antes de cadastro)
            AcompanharPedidoAgent(),   # Prioridade 120 - verificar antes de iniciar pedido
            IniciarPedidoAgent(),      # Prioridade 100 - verificado segundo
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

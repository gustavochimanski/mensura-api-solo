"""
Utilitários para normalização e extração de dados de mensagens
"""
import re
import unicodedata
from typing import Dict, Any, List, Optional


class MensagemUtils:
    """
    Classe com métodos utilitários para normalização e extração de dados de mensagens.
    Todos os métodos são estáticos (funções puras).
    """

    @staticmethod
    def normalizar_mensagem(mensagem: str) -> str:
        """
        Normaliza a mensagem para regras simples:
        - remove acentos
        - troca pontuação por espaço
        - colapsa espaços
        """
        msg = (mensagem or "").lower().strip()
        msg = (
            msg.replace("´", "'")
            .replace("`", "'")
            .replace("’", "'")
            .replace("‘", "'")
        )
        msg = unicodedata.normalize("NFKD", msg)
        msg = "".join(ch for ch in msg if not unicodedata.combining(ch))
        msg = re.sub(r"[^a-z0-9\s]", " ", msg)
        msg = re.sub(r"\s+", " ", msg).strip()
        return msg

    @staticmethod
    def extrair_quantidade_pergunta(pergunta: str, nome_produto: str) -> int:
        """
        Extrai quantidade da pergunta quando o cliente pergunta preço com quantidade.
        Ex: "quanto fica 6 coca" -> 6
        """
        if not pergunta:
            return 1

        msg = MensagemUtils.normalizar_mensagem(pergunta)
        if not msg:
            return 1

        nome_norm = MensagemUtils.normalizar_mensagem(nome_produto)
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

    @staticmethod
    def extrair_itens_pergunta_preco(mensagem: str) -> List[Dict[str, Any]]:
        """
        Extrai itens e quantidades em perguntas de preço com múltiplos produtos.
        Ex: "quanto fica 2 x bacon e 1 coca lata" -> [{"produto_busca": "x bacon", "quantidade": 2}, ...]
        """
        msg = MensagemUtils.normalizar_mensagem(mensagem)
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

    @staticmethod
    def extrair_itens_pedido(mensagem: str) -> List[Dict[str, Any]]:
        """
        Extrai itens e quantidades de pedidos com múltiplos produtos.
        Ex: "não, vou querer apenas 1 x bacon e 1 coca" -> [{"produto_busca": "x bacon", "quantidade": 1}, ...]
        """
        msg = MensagemUtils.normalizar_mensagem(mensagem)
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

    @staticmethod
    def extrair_quantidade(mensagem: str) -> int:
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

    @staticmethod
    def extrair_numero(mensagem: str) -> Optional[int]:
        """Extrai número da mensagem"""
        msg = mensagem.strip()
        if msg.isdigit():
            return int(msg)
        # Tenta extrair primeiro número da mensagem
        match = re.search(r'\d+', msg)
        if match:
            return int(match.group())
        return None

    @staticmethod
    def extrair_numero_natural(mensagem: str, max_opcoes: int = 10) -> Optional[int]:
        """
        Extrai número da mensagem, incluindo linguagem natural.
        Detecta: "primeiro", "segundo", "pode ser o 1", "esse mesmo", etc.
        """
        msg = mensagem.lower().strip()

        # Primeiro tenta extrair número direto
        numero_direto = MensagemUtils.extrair_numero(mensagem)
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
            'esse mesmo ai', 'essa mesma ai', 'pode ser esse', 'pode ser essa',
            'esse', 'essa', 'o primeiro', 'a primeira'
        ]
        for frase in frases_primeiro:
            if frase in msg:
                return 1

        return None

    @staticmethod
    def extrair_endereco_heuristica(mensagem: str) -> str:
        """
        Extrai endereço de uma mensagem de forma heurística.
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

    @staticmethod
    def parece_endereco(mensagem: str) -> bool:
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
        return tem_numero and tem_indicador

import re
from typing import List, Optional


def variantes_celular_para_busca(telefone_normalizado: Optional[str]) -> List[str]:
    """
    Retorna o número e suas variantes com/sem o "9" de celular para busca.
    Usado no login/cadastro: se o usuário logar com um 9 a menos (ex: 1189999999)
    e no banco estiver com o 9 (11999999999), ainda encontra o cliente.

    - Número com 10 dígitos nacionais (DDD + 8): adiciona variante "com 9 a mais".
    - Número com 11 dígitos nacionais (DDD + 9 + 8) e 3º dígito "9": adiciona variante "com 9 a menos".
    """
    if not telefone_normalizado or len(telefone_normalizado) < 10:
        return []
    base = telefone_normalizado.strip()
    out: List[str] = [base]
    if base.startswith("55") and len(base) >= 4:
        nacional = base[2:]  # sem 55
        if len(nacional) == 10:
            # DDD(2) + 8 dígitos → variante com 9 a mais: DDD + "9" + 8
            v_mais = "55" + nacional[:2] + "9" + nacional[2:]
            if v_mais not in out:
                out.append(v_mais)
        if len(nacional) == 11 and nacional[2] == "9":
            # DDD(2) + 9 + 8 dígitos → variante com 9 a menos
            v_menos = "55" + nacional[:2] + nacional[3:]
            if v_menos not in out:
                out.append(v_menos)
    return out


def normalizar_telefone(telefone: Optional[str]) -> Optional[str]:
    """
    Normaliza o número de telefone removendo caracteres não numéricos e
    garantindo o prefixo do país (55) quando for um número brasileiro.

    Regras:
    - Remove máscara: espaços, parênteses, hífen, '+' etc.
    - Remove prefixo internacional "00" (ex: 0055...).
    - Se não começar com "55" e tiver 10 ou 11 dígitos (formato BR sem país),
      prefixa com "55".
    - Se tiver menos de 10 dígitos (número incompleto), também prefixa com "55"
      (mantém comportamento já usado no serviço de clientes).
    
    IMPORTANTE: NÃO adiciona dígitos como "9" - usa o número EXATAMENTE como recebido.
    """
    if telefone is None:
        return None

    telefone_limpo = re.sub(r"[^\d]", "", telefone)
    if not telefone_limpo:
        return telefone_limpo

    # Ex.: 0055...
    if telefone_limpo.startswith("00"):
        telefone_limpo = telefone_limpo[2:]

    # Ex.: 0 + DDD + número (variações)
    # Remove apenas se não começar com 55 e tiver 11 ou 12 dígitos
    if telefone_limpo.startswith("0") and not telefone_limpo.startswith("55") and len(telefone_limpo) in (11, 12):
        telefone_limpo = telefone_limpo.lstrip("0")

    if telefone_limpo.startswith("55"):
        return telefone_limpo

    # Números BR sem código do país (DDD + número)
    # IMPORTANTE: NÃO adiciona "9" para números de 10 dígitos - usa exatamente como recebido
    if len(telefone_limpo) in (10, 11) or len(telefone_limpo) < 10:
        return "55" + telefone_limpo

    return telefone_limpo


import re
from typing import Optional


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


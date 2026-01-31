import re
from typing import List, Optional, Iterable, Set, Tuple


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


def _split_br_ddd_assinante(digits: str) -> Optional[Tuple[str, str, bool]]:
    """
    Tenta extrair (DDD, assinante, tem_pais_55) a partir de uma string somente dígitos.
    Aceita:
    - 55 + DDD + (8 ou 9 dígitos)
    - DDD + (8 ou 9 dígitos)
    """
    if not digits:
        return None

    d = str(digits)

    # Ex.: 0055...
    if d.startswith("00") and len(d) > 2:
        d = d[2:]

    # Ex.: 0 + DDD + número (variações)
    if d.startswith("0") and not d.startswith("55") and len(d) in (11, 12):
        d = d.lstrip("0")

    if d.startswith("55"):
        rest = d[2:]
        if len(rest) < 10:
            return None
        ddd = rest[:2]
        assinante = rest[2:]
        return ddd, assinante, True

    # BR sem código do país: DDD + número
    if len(d) in (10, 11):
        ddd = d[:2]
        assinante = d[2:]
        return ddd, assinante, False

    return None


def _pode_inserir_nono_digito(assinante_8: str) -> bool:
    """
    Regra prática para BR:
    - celulares antigos tinham 8 dígitos e começavam tipicamente com 6-9
    - fixos/landlines tendem a começar com 2-5 (não inserir 9)
    """
    if not assinante_8 or len(assinante_8) != 8:
        return False
    return assinante_8[0] in {"6", "7", "8", "9"}


def normalizar_telefone_para_armazenar(telefone: Optional[str]) -> Optional[str]:
    """
    Normaliza telefone para persistir no banco de forma consistente:
    - remove máscara
    - garante prefixo 55 quando for BR
    - quando for BR com DDD + 8 dígitos e parecer celular, INSERE o 9

    Objetivo: salvar preferencialmente como 55 + DDD + 9 dígitos (celular).
    """
    if telefone is None:
        return None

    digits = re.sub(r"[^\d]", "", str(telefone))
    if not digits:
        return digits

    split = _split_br_ddd_assinante(digits)
    if not split:
        # fallback: mantém o comportamento anterior (ao menos tenta prefixar 55 quando aplicável)
        return normalizar_telefone(str(telefone))

    ddd, assinante, _tem_55 = split

    # Se veio com 8 dígitos nacionais e parece celular, insere 9 (DDD + 9 + 8)
    if len(assinante) == 8 and _pode_inserir_nono_digito(assinante):
        assinante = "9" + assinante

    # Se veio com 10 dígitos nacionais (55DD + 8 dígitos) ou 12 total, normaliza para 13 quando celular
    out = "55" + ddd + assinante

    # Se veio com um "9" duplicado após o DDD (ex.: 55DD99XXXXXXXX), remove o excesso
    if out.startswith("55") and len(out) == 14 and out[4:6] == "99":
        out = out[:5] + out[6:]

    return out


def variantes_telefone_para_busca(telefone: Optional[str]) -> List[str]:
    """
    Gera variantes para busca/consulta/login aceitando:
    - com/sem 55
    - com/sem o 9 de celular (quando aplicável)
    """
    if telefone is None:
        return []

    digits = re.sub(r"[^\d]", "", str(telefone))
    if not digits:
        return []

    # Base normalizada (mantém compatibilidade com comportamento antigo)
    base = normalizar_telefone(str(telefone)) or digits

    out: Set[str] = set()
    out.add(base)
    out.add(digits)

    split = _split_br_ddd_assinante(digits)
    if not split:
        # fallback: se já estiver com 55, tenta também sem 55 (bases antigas)
        if base.startswith("55") and len(base) > 2:
            out.add(base[2:])
        return [x for x in out if x]

    ddd, assinante, tem_55 = split

    # Deriva assinante com e sem 9
    assinante_8: Optional[str] = None
    assinante_9: Optional[str] = None

    if len(assinante) == 9:
        assinante_9 = assinante
        if assinante.startswith("9"):
            assinante_8 = assinante[1:]
    elif len(assinante) == 8:
        assinante_8 = assinante
        if _pode_inserir_nono_digito(assinante):
            assinante_9 = "9" + assinante

    # Monta variantes com/sem 55
    def _add(v: Optional[str]) -> None:
        if v:
            out.add(v)

    for a in (assinante_8, assinante_9):
        if not a:
            continue
        _add("55" + ddd + a)
        _add(ddd + a)

    # Compatibilidade: se base veio com 55, tenta sem 55 também
    if base.startswith("55") and len(base) > 2:
        out.add(base[2:])

    # Retorna estável (mas sem garantir ordem específica além de determinística)
    return sorted([x for x in out if x], key=lambda s: (len(s), s))


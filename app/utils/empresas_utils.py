from typing import Callable

def normalizar_empresas(
    empresas_raw: list[str | int] | None,
    buscar_empresas_ativas: Callable[[], list[int]]
) -> list[str]:
    """
    Normaliza a lista de empresas:
    - Remove valores inválidos (vazios, '0', '000', None, etc.)
    - Converte para string com 3 dígitos (zfill)
    - Se ficar vazio, busca as empresas ativas via repositório
    """
    if not empresas_raw:
        empresas_raw = []

    empresas_validas = []
    for e in empresas_raw:
        try:
            e_int = int(str(e))
            if e_int > 0:
                empresas_validas.append(str(e_int).zfill(3))
        except ValueError:
            continue

    if not empresas_validas:
        empresas_ativas = buscar_empresas_ativas()
        empresas_validas = [str(c).zfill(3) for c in empresas_ativas]

    return empresas_validas

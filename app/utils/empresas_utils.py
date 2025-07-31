def normalizar_empresas(empresas_raw: list | None, buscar_empresas_ativas: callable) -> list[str]:
    """
    - Remove vazios, None, 0 e converte para string com zero à esquerda (3 dígitos).
    - Se o resultado for vazio, busca empresas ativas com o repositório passado.
    """
    if not empresas_raw:
        empresas_raw = []

    # Filtra valores úteis
    empresas_filtradas = [
        str(e).zfill(3)
        for e in empresas_raw
        if str(e).isdigit() and int(e) > 0
    ]

    if not empresas_filtradas:
        empresas_ativas = buscar_empresas_ativas()
        return [str(e).zfill(3) for e in empresas_ativas]

    return empresas_filtradas

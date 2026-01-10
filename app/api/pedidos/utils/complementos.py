from __future__ import annotations

from decimal import Decimal
from typing import Sequence, List, Dict, Any

from app.api.catalogo.contracts.complemento_contract import IComplementoContract, ComplementoDTO, AdicionalDTO


def _coerce_quantidade(value) -> int:
    try:
        quantidade = int(value or 1)
    except (TypeError, ValueError):
        quantidade = 1
    return 1 if quantidade < 1 else quantidade


def resolve_produto_complementos(
    *,
    complemento_contract: IComplementoContract | None,
    produto_cod_barras: str,
    complementos_request: Sequence | None,
    quantidade_item: int,
) -> tuple[Decimal, List[Dict[str, Any]]]:
    """
    Calcula o total de complementos e adicionais de um item (produto com código de barras) e
    retorna também um snapshot serializável para respostas.
    
    Args:
        complemento_contract: Contrato para buscar complementos
        produto_cod_barras: Código de barras do produto
        complementos_request: Lista de complementos com seus adicionais selecionados
        quantidade_item: Quantidade do item no pedido
    
    Returns:
        Tupla com (total_decimal, snapshot_list)
    """
    quantidade_item = _coerce_quantidade(quantidade_item)
    if complemento_contract is None or not produto_cod_barras:
        return Decimal("0"), []

    if not complementos_request:
        return Decimal("0"), []

    # Coleta todos os IDs de complementos
    complemento_ids = []
    complemento_adicionais_map: Dict[int, List[Dict[str, int]]] = {}
    
    for comp_req in complementos_request:
        complemento_id = getattr(comp_req, "complemento_id", None)
        if complemento_id is None:
            continue
        
        complemento_ids.append(complemento_id)
        adicionais_req = getattr(comp_req, "adicionais", []) or []
        
        # Mapeia adicionais por complemento
        complemento_adicionais_map[complemento_id] = [
            {
                "adicional_id": getattr(ad, "adicional_id", None),
                "quantidade": _coerce_quantidade(getattr(ad, "quantidade", 1)),
            }
            for ad in adicionais_req
            if getattr(ad, "adicional_id", None) is not None
        ]

    if not complemento_ids:
        return Decimal("0"), []

    # Busca complementos do produto
    complementos_db = complemento_contract.buscar_por_ids_para_produto(produto_cod_barras, complemento_ids)
    if not complementos_db:
        return Decimal("0"), []

    total = Decimal("0")
    snapshot: List[Dict[str, Any]] = []

    for complemento in complementos_db:
        complemento_id = complemento.id
        adicionais_selecionados = complemento_adicionais_map.get(complemento_id, [])
        
        if not adicionais_selecionados:
            continue

        # Cria mapa de adicionais do complemento por ID
        adicionais_por_id: Dict[int, AdicionalDTO] = {
            a.id: a for a in complemento.adicionais
        }

        complemento_total = Decimal("0")
        complemento_snapshot: List[Dict[str, Any]] = []

        for ad_req in adicionais_selecionados:
            adicional_id = ad_req.get("adicional_id")
            quantidade_adicional = ad_req.get("quantidade", 1)
            
            if adicional_id not in adicionais_por_id:
                continue

            adicional = adicionais_por_id[adicional_id]
            
            # Se o complemento não for quantitativo, força quantidade = 1
            if not complemento.quantitativo:
                quantidade_adicional = 1

            preco_unitario = Decimal(str(adicional.preco or 0))
            subtotal = preco_unitario * quantidade_adicional * quantidade_item
            complemento_total += subtotal

            complemento_snapshot.append({
                "adicional_id": adicional_id,
                "nome": adicional.nome,
                "quantidade": quantidade_adicional,
                "preco_unitario": float(preco_unitario),
                "total": float(subtotal),
            })

        if complemento_snapshot:
            total += complemento_total
            snapshot.append({
                "complemento_id": complemento_id,
                "complemento_nome": complemento.nome,
                "obrigatorio": complemento.obrigatorio,
                "quantitativo": complemento.quantitativo,
                "total": float(complemento_total),
                "adicionais": complemento_snapshot,
            })

    return total, snapshot


def resolve_complementos_diretos(
    *,
    complemento_contract: IComplementoContract | None,
    empresa_id: int,
    complementos_request: Sequence | None,
    quantidade_item: int,
    combo_id: int | None = None,
    receita_id: int | None = None,
) -> tuple[Decimal, List[Dict[str, Any]]]:
    """
    Calcula o total de complementos e adicionais diretamente pelos IDs (para receitas e combos).
    Não precisa de código de barras, apenas dos IDs dos complementos e adicionais.
    
    Args:
        complemento_contract: Contrato para buscar complementos
        empresa_id: ID da empresa
        complementos_request: Lista de complementos com seus adicionais selecionados
        quantidade_item: Quantidade do item no pedido
        combo_id: ID do combo (opcional, para validar vínculos)
        receita_id: ID da receita (opcional, para validar vínculos)
    
    Returns:
        Tupla com (total_decimal, snapshot_list)
    """
    quantidade_item = _coerce_quantidade(quantidade_item)
    if complemento_contract is None:
        return Decimal("0"), []

    if not complementos_request:
        return Decimal("0"), []

    # Coleta todos os IDs de complementos
    complemento_ids = []
    complemento_adicionais_map: Dict[int, List[Dict[str, int]]] = {}
    
    for comp_req in complementos_request:
        complemento_id = getattr(comp_req, "complemento_id", None)
        if complemento_id is None:
            continue
        
        complemento_ids.append(complemento_id)
        adicionais_req = getattr(comp_req, "adicionais", []) or []
        
        # Mapeia adicionais por complemento
        complemento_adicionais_map[complemento_id] = [
            {
                "adicional_id": getattr(ad, "adicional_id", None),
                "quantidade": _coerce_quantidade(getattr(ad, "quantidade", 1)),
            }
            for ad in adicionais_req
            if getattr(ad, "adicional_id", None) is not None
        ]

    if not complemento_ids:
        return Decimal("0"), []

    # Busca complementos: se for combo, usa listar_por_combo para validar vínculos
    if combo_id is not None:
        combo_id_int = int(combo_id) if not isinstance(combo_id, int) else combo_id
        complementos_db_all = complemento_contract.listar_por_combo(combo_id_int, apenas_ativos=True)
        ids_set = set(complemento_ids)
        complementos_db = [c for c in complementos_db_all if c.id in ids_set]
    elif receita_id is not None:
        receita_id_int = int(receita_id) if not isinstance(receita_id, int) else receita_id
        complementos_db_all = complemento_contract.listar_por_receita(receita_id_int, apenas_ativos=True)
        ids_set = set(complemento_ids)
        complementos_db = [c for c in complementos_db_all if c.id in ids_set]
    else:
        # Fallback: busca por empresa (menos seguro, mas funciona)
        complementos_db = complemento_contract.buscar_por_ids(empresa_id, complemento_ids)
    
    if not complementos_db:
        return Decimal("0"), []

    total = Decimal("0")
    snapshot: List[Dict[str, Any]] = []

    for complemento in complementos_db:
        complemento_id = complemento.id
        adicionais_selecionados = complemento_adicionais_map.get(complemento_id, [])
        
        if not adicionais_selecionados:
            continue

        # Cria mapa de adicionais do complemento por ID
        adicionais_por_id: Dict[int, AdicionalDTO] = {
            a.id: a for a in complemento.adicionais
        }

        complemento_total = Decimal("0")
        complemento_snapshot: List[Dict[str, Any]] = []

        for ad_req in adicionais_selecionados:
            adicional_id = ad_req.get("adicional_id")
            quantidade_adicional = ad_req.get("quantidade", 1)
            
            if adicional_id not in adicionais_por_id:
                continue

            adicional = adicionais_por_id[adicional_id]
            
            # Se o complemento não for quantitativo, força quantidade = 1
            if not complemento.quantitativo:
                quantidade_adicional = 1

            preco_unitario = Decimal(str(adicional.preco or 0))
            subtotal = preco_unitario * quantidade_adicional * quantidade_item
            complemento_total += subtotal

            complemento_snapshot.append({
                "adicional_id": adicional_id,
                "nome": adicional.nome,
                "quantidade": quantidade_adicional,
                "preco_unitario": float(preco_unitario),
                "total": float(subtotal),
            })

        if complemento_snapshot:
            total += complemento_total
            snapshot.append({
                "complemento_id": complemento_id,
                "complemento_nome": complemento.nome,
                "obrigatorio": complemento.obrigatorio,
                "quantitativo": complemento.quantitativo,
                "total": float(complemento_total),
                "adicionais": complemento_snapshot,
            })

    return total, snapshot


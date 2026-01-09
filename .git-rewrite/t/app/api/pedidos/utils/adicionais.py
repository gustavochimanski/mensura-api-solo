from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Iterable, Sequence


def _coerce_quantidade(value) -> int:
    try:
        quantidade = int(value or 1)
    except (TypeError, ValueError):
        quantidade = 1
    return 1 if quantidade < 1 else quantidade


def _ensure_requests(
    adicionais_request: Sequence | None,
    adicionais_ids: Sequence[int] | None,
) -> list:
    if adicionais_request:
        return list(adicionais_request)
    if adicionais_ids:
        return [SimpleNamespace(adicional_id=ad_id, quantidade=1) for ad_id in adicionais_ids]
    return []


def resolve_produto_adicionais(
    *,
    adicional_contract,
    produto_cod_barras: str,
    adicionais_request: Sequence | None,
    adicionais_ids: Sequence[int] | None,
    quantidade_item: int,
) -> tuple[Decimal, list[dict]]:
    """
    Calcula o total de adicionais de um item (produto com código de barras) e
    retorna também um snapshot serializável para respostas.
    """
    quantidade_item = _coerce_quantidade(quantidade_item)
    if adicional_contract is None or not produto_cod_barras:
        return Decimal("0"), []

    requests = _ensure_requests(adicionais_request, adicionais_ids)
    if not requests:
        return Decimal("0"), []

    adicional_ids = [
        getattr(req, "adicional_id", None)
        for req in requests
        if getattr(req, "adicional_id", None) is not None
    ]
    if not adicional_ids:
        return Decimal("0"), []

    adicionais_db = adicional_contract.buscar_por_ids_para_produto(produto_cod_barras, adicional_ids)
    if not adicionais_db:
        return Decimal("0"), []

    quantidade_por_id = {}
    for req in requests:
        adicional_id = getattr(req, "adicional_id", None)
        if adicional_id is None:
            continue
        quantidade_por_id[adicional_id] = _coerce_quantidade(getattr(req, "quantidade", 1))

    total = Decimal("0")
    snapshot: list[dict] = []
    for adicional in adicionais_db:
        adicional_id = getattr(adicional, "id", None)
        if adicional_id is None:
            continue
        quantidade_por_item = quantidade_por_id.get(adicional_id, 1)
        preco_unitario = Decimal(str(getattr(adicional, "preco", 0) or 0))
        subtotal = preco_unitario * quantidade_por_item * quantidade_item
        total += subtotal
        snapshot.append(
            {
                "adicional_id": adicional_id,
                "nome": getattr(adicional, "nome", None),
                "quantidade": quantidade_por_item,
                "preco_unitario": float(preco_unitario),
                "total": float(subtotal),
            }
        )

    return total, snapshot


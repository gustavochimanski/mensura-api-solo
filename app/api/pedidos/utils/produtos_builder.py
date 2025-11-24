from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Any

from pydantic import ValidationError

from app.api.pedidos.schemas.schema_pedido import (
    ProdutosPedidoOut,
    ProdutoPedidoItemOut,
    ProdutoPedidoAdicionalOut,
)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_adicionais_out(snapshot) -> list[ProdutoPedidoAdicionalOut]:
    if not snapshot:
        return []
    adicionais_out: list[ProdutoPedidoAdicionalOut] = []
    for adicional in snapshot:
        try:
            adicionais_out.append(
                ProdutoPedidoAdicionalOut(
                    adicional_id=getattr(adicional, "adicional_id", None)
                    if not isinstance(adicional, dict)
                    else adicional.get("adicional_id"),
                    nome=getattr(adicional, "nome", None)
                    if not isinstance(adicional, dict)
                    else adicional.get("nome"),
                    quantidade=getattr(adicional, "quantidade", None)
                    if not isinstance(adicional, dict)
                    else adicional.get("quantidade", 1),
                    preco_unitario=_to_float(
                        getattr(adicional, "preco_unitario", None)
                        if not isinstance(adicional, dict)
                        else adicional.get("preco_unitario")
                    ),
                    total=_to_float(
                        getattr(adicional, "total", None)
                        if not isinstance(adicional, dict)
                        else adicional.get("total")
                    ),
                )
            )
        except ValidationError:
            continue
    return adicionais_out


def build_produtos_out_from_items(
    itens: Iterable[Any] | None,
    snapshot: dict | ProdutosPedidoOut | None = None,
) -> ProdutosPedidoOut:
    itens_out: list[ProdutoPedidoItemOut] = []
    for item in itens or []:
        adicionais_snapshot = getattr(item, "adicionais_snapshot", None)
        itens_out.append(
            ProdutoPedidoItemOut(
                item_id=getattr(item, "id", None),
                produto_cod_barras=getattr(item, "produto_cod_barras", None),
                descricao=getattr(item, "produto_descricao_snapshot", None),
                imagem=getattr(item, "produto_imagem_snapshot", None),
                quantidade=getattr(item, "quantidade", 0) or 0,
                preco_unitario=_to_float(getattr(item, "preco_unitario", 0)),
                observacao=getattr(item, "observacao", None),
                adicionais=_build_adicionais_out(adicionais_snapshot),
            )
        )

    snapshot_model: ProdutosPedidoOut | None = None
    if snapshot is not None:
        if isinstance(snapshot, ProdutosPedidoOut):
            snapshot_model = snapshot
        else:
            try:
                snapshot_model = ProdutosPedidoOut.model_validate(snapshot)
            except ValidationError:
                snapshot_model = None

    receitas = snapshot_model.receitas if snapshot_model else []
    combos = snapshot_model.combos if snapshot_model else []

    return ProdutosPedidoOut(
        itens=itens_out,
        receitas=receitas,
        combos=combos,
    )


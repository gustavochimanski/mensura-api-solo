from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Any

from pydantic import ValidationError

from app.api.pedidos.schemas.schema_pedido import (
    ProdutosPedidoOut,
    ProdutoPedidoItemOut,
    ProdutoPedidoAdicionalOut,
    ComplementoPedidoOut,
    ReceitaPedidoOut,
    ComboPedidoOut,
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


def _build_adicionais_out(adicionais_list) -> list[ProdutoPedidoAdicionalOut]:
    """Constrói lista de adicionais a partir de uma lista de adicionais."""
    if not adicionais_list:
        return []
    adicionais_out: list[ProdutoPedidoAdicionalOut] = []
    for adicional in adicionais_list:
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


def _build_complementos_out(complementos_snapshot) -> list[ComplementoPedidoOut]:
    """Constrói lista de complementos a partir do snapshot de complementos."""
    if not complementos_snapshot:
        return []
    complementos_out: list[ComplementoPedidoOut] = []
    for complemento in complementos_snapshot:
        try:
            # O snapshot pode ser dict ou objeto
            if isinstance(complemento, dict):
                complemento_id = complemento.get("complemento_id")
                complemento_nome = complemento.get("complemento_nome", "")
                obrigatorio = complemento.get("obrigatorio", False)
                quantitativo = complemento.get("quantitativo", False)
                total = _to_float(complemento.get("total", 0))
                adicionais_list = complemento.get("adicionais", [])
            else:
                complemento_id = getattr(complemento, "complemento_id", None)
                complemento_nome = getattr(complemento, "complemento_nome", "")
                obrigatorio = getattr(complemento, "obrigatorio", False)
                quantitativo = getattr(complemento, "quantitativo", False)
                total = _to_float(getattr(complemento, "total", 0))
                adicionais_list = getattr(complemento, "adicionais", [])
            
            if complemento_id is None:
                continue
                
            complementos_out.append(
                ComplementoPedidoOut(
                    complemento_id=complemento_id,
                    complemento_nome=complemento_nome,
                    obrigatorio=obrigatorio,
                    quantitativo=quantitativo,
                    total=total,
                    adicionais=_build_adicionais_out(adicionais_list),
                )
            )
        except ValidationError:
            continue
    return complementos_out


def build_produtos_out_from_items(
    itens: Iterable[Any] | None,
    snapshot: dict | ProdutosPedidoOut | None = None,
) -> ProdutosPedidoOut:
    itens_out: list[ProdutoPedidoItemOut] = []
    receitas_out: list[ReceitaPedidoOut] = []
    combos_out: list[ComboPedidoOut] = []
    
    for item in itens or []:
        complementos_snapshot = getattr(item, "adicionais_snapshot", None)
        # O snapshot de adicionais_snapshot na verdade contém complementos com adicionais dentro
        
        item_id = getattr(item, "id", None)
        produto_cod_barras = getattr(item, "produto_cod_barras", None)
        receita_id = getattr(item, "receita_id", None)
        combo_id = getattr(item, "combo_id", None)
        
        # Determina o tipo do item
        if produto_cod_barras:
            # É um produto
            itens_out.append(
                ProdutoPedidoItemOut(
                    item_id=item_id,
                    produto_cod_barras=produto_cod_barras,
                    descricao=getattr(item, "produto_descricao_snapshot", None),
                    imagem=getattr(item, "produto_imagem_snapshot", None),
                    quantidade=getattr(item, "quantidade", 0) or 0,
                    preco_unitario=_to_float(getattr(item, "preco_unitario", 0)),
                    observacao=getattr(item, "observacao", None),
                    complementos=_build_complementos_out(complementos_snapshot),
                )
            )
        elif receita_id:
            # É uma receita
            receitas_out.append(
                ReceitaPedidoOut(
                    item_id=item_id,
                    receita_id=receita_id,
                    nome=getattr(item, "produto_descricao_snapshot", None),
                    quantidade=getattr(item, "quantidade", 0) or 0,
                    preco_unitario=_to_float(getattr(item, "preco_unitario", 0)),
                    observacao=getattr(item, "observacao", None),
                    complementos=_build_complementos_out(complementos_snapshot),
                )
            )
        elif combo_id:
            # É um combo
            combos_out.append(
                ComboPedidoOut(
                    combo_id=combo_id,
                    nome=getattr(item, "produto_descricao_snapshot", None),
                    quantidade=getattr(item, "quantidade", 0) or 0,
                    preco_unitario=_to_float(getattr(item, "preco_unitario", 0)),
                    observacao=getattr(item, "observacao", None),
                    complementos=_build_complementos_out(complementos_snapshot),
                )
            )

    # Se houver snapshot adicional (legado), mescla com os dados dos itens
    snapshot_model: ProdutosPedidoOut | None = None
    if snapshot is not None:
        if isinstance(snapshot, ProdutosPedidoOut):
            snapshot_model = snapshot
        else:
            try:
                snapshot_model = ProdutosPedidoOut.model_validate(snapshot)
            except ValidationError:
                snapshot_model = None

    # Mescla receitas e combos do snapshot (se houver) com os processados dos itens
    if snapshot_model:
        receitas_out.extend(snapshot_model.receitas)
        combos_out.extend(snapshot_model.combos)

    return ProdutosPedidoOut(
        itens=itens_out,
        receitas=receitas_out,
        combos=combos_out,
    )


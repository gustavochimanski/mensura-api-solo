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
    """Constrói lista de adicionais a partir das relações SQLAlchemy (PedidoItemComplementoAdicionalModel)."""
    if not adicionais_list:
        return []
    adicionais_out: list[ProdutoPedidoAdicionalOut] = []
    for adicional in adicionais_list:
        try:
            # Usa o modelo relacional PedidoItemComplementoAdicionalModel
            adicionais_out.append(
                ProdutoPedidoAdicionalOut(
                    adicional_id=getattr(adicional, "adicional_id", None),
                    nome=getattr(adicional, "nome", None),
                    quantidade=int(getattr(adicional, "quantidade", 1) or 1),
                    preco_unitario=_to_float(getattr(adicional, "preco_unitario", 0)),
                    total=_to_float(getattr(adicional, "total", 0)),
                )
            )
        except ValidationError:
            continue
    return adicionais_out


def _build_complementos_out(complementos_rel) -> list[ComplementoPedidoOut]:
    """Constrói lista de complementos a partir das relações SQLAlchemy."""
    if not complementos_rel:
        return []
    complementos_out: list[ComplementoPedidoOut] = []
    for complemento in complementos_rel:
        try:
            # Usa o modelo relacional PedidoItemComplementoModel
            complemento_id = getattr(complemento, "complemento_id", None)
            complemento_nome = getattr(complemento, "complemento_nome", "") or ""
            obrigatorio = bool(getattr(complemento, "obrigatorio", False))
            quantitativo = bool(getattr(complemento, "quantitativo", False))
            total = _to_float(getattr(complemento, "total", 0))
            adicionais_list = getattr(complemento, "adicionais", []) or []
            
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
        # Usa modelo relacional (PedidoItemComplementoModel via relação item.complementos)
        complementos_rel = getattr(item, "complementos", None) or []
        
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
                    complementos=_build_complementos_out(complementos_rel),
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
                    complementos=_build_complementos_out(complementos_rel),
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
                    complementos=_build_complementos_out(complementos_rel),
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


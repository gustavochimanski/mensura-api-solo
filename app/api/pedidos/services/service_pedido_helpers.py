from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Optional

from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
from app.api.pedidos.schemas.schema_pedido import PedidoPagamentoResumo
from app.api.shared.schemas.schema_shared_enums import (
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
)


def _dec(value: float | Decimal | int) -> Decimal:
    """Converte valor para Decimal com precisão de 2 casas decimais."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ajustar_pagamento_dinheiro_com_troco(
    *,
    pagamentos: list[dict],
    valor_total: Decimal,
    is_dinheiro: Callable[[int], bool],
) -> tuple[list[dict], Decimal | None]:
    """
    Normaliza payloads onde o frontend envia o *valor recebido* em DINHEIRO no campo `valor`.

    Regra:
    - Se existir exatamente 1 pagamento e `valor > valor_total`, isso só é permitido para DINHEIRO.
      Nesse caso:
        - retorna `troco_para` (= valor recebido)
        - ajusta o pagamento para `valor_total` (valor efetivamente aplicado ao pedido)

    Observação:
    - Para múltiplos meios, um `valor > valor_total` é considerado inválido (troco ficaria ambíguo).
    """

    if not pagamentos:
        return pagamentos, None

    # Coage/normaliza valores (defensivo)
    pagamentos_norm = [
        {"meio_pagamento_id": int(p.get("meio_pagamento_id")), "valor": _dec(p.get("valor", 0) or 0)}
        for p in pagamentos
        if p.get("meio_pagamento_id") is not None
    ]
    if not pagamentos_norm:
        return [], None

    if len(pagamentos_norm) != 1:
        # Se tiver múltiplos meios, não aceitamos "valor recebido" maior que o total em nenhum item.
        if any(p["valor"] > valor_total for p in pagamentos_norm):
            raise ValueError(
                "Pagamento com valor maior que o total não é suportado com múltiplos meios (troco ambíguo)."
            )
        return pagamentos_norm, None

    p0 = pagamentos_norm[0]
    if p0["valor"] <= valor_total:
        return pagamentos_norm, None

    mp_id = int(p0["meio_pagamento_id"])
    if not is_dinheiro(mp_id):
        raise ValueError("Pagamento maior que o total só é permitido para meio de pagamento do tipo DINHEIRO.")

    troco_para = p0["valor"]
    return [{"meio_pagamento_id": mp_id, "valor": valor_total}], troco_para


def _safe_enum(enum_cls, value):
    """Safely converte um valor para um enum, retornando None se inválido."""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def build_pagamento_resumo(pedido: PedidoUnificadoModel) -> PedidoPagamentoResumo | None:
    """Constrói resumo de pagamento a partir do pedido."""
    transacoes = list(getattr(pedido, "transacoes", None) or [])
    transacao = getattr(pedido, "transacao", None)
    if transacao is not None:
        # Compat: se existir relacionamento singular preenchido, inclui na lista
        transacoes = [transacao] + [t for t in transacoes if getattr(t, "id", None) != getattr(transacao, "id", None)]

    def _tx_sort_key(tx):
        return (
            getattr(tx, "pago_em", None)
            or getattr(tx, "autorizado_em", None)
            or getattr(tx, "updated_at", None)
            or getattr(tx, "created_at", None)
        )

    # Garante uma ordenação consistente (mais recente primeiro) para o "resumo principal".
    try:
        transacoes.sort(key=_tx_sort_key, reverse=True)
    except Exception:
        pass

    meio_pagamento_rel = getattr(pedido, "meio_pagamento", None)
    meio_pagamento_id = getattr(pedido, "meio_pagamento_id", None)

    # Se existir ao menos uma transação, usa a primeira como referência de "principal"
    if transacoes:
        tx0 = transacoes[0]
        if getattr(tx0, "meio_pagamento", None) is not None:
            meio_pagamento_rel = tx0.meio_pagamento
        if getattr(tx0, "meio_pagamento_id", None) is not None:
            meio_pagamento_id = tx0.meio_pagamento_id

    if not transacoes and meio_pagamento_rel is None and meio_pagamento_id is None:
        return None

    status = None
    metodo = None
    gateway = None
    provider_transaction_id = None
    valor_total = float(pedido.valor_total or 0)
    valor = valor_total
    atualizado_em = getattr(pedido, "updated_at", None)

    if transacoes:
        # Resumo "principal" = primeira transação (mais recente, conforme query)
        tx0 = transacoes[0]
        status = _safe_enum(PagamentoStatusEnum, getattr(tx0, "status", None))
        metodo = _safe_enum(PagamentoMetodoEnum, getattr(tx0, "metodo", None))
        gateway = _safe_enum(PagamentoGatewayEnum, getattr(tx0, "gateway", None))
        provider_transaction_id = getattr(tx0, "provider_transaction_id", None)

        # valor do resumo (principal) = valor da tx0, mas mantemos cálculo total separadamente
        if getattr(tx0, "valor", None) is not None:
            valor = float(tx0.valor)

        atualizado_em = (
            getattr(tx0, "pago_em", None)
            or getattr(tx0, "autorizado_em", None)
            or getattr(tx0, "cancelado_em", None)
            or getattr(tx0, "estornado_em", None)
            or getattr(tx0, "updated_at", None)
            or getattr(tx0, "created_at", None)
        )

    # Regra de negócio:
    # - Ter meio de pagamento NÃO implica que está pago.
    # - Considera "pago" APENAS via transações (status PAGO/AUTORIZADO).
    #   O campo `pago` não é mais persistido no pedido.
    valor_pago = Decimal("0.00")
    for tx in transacoes:
        st = _safe_enum(PagamentoStatusEnum, getattr(tx, "status", None))
        if st in {PagamentoStatusEnum.PAGO, PagamentoStatusEnum.AUTORIZADO}:
            try:
                valor_pago += _dec(getattr(tx, "valor", 0) or 0)
            except Exception:
                continue
    tx_pago_total = valor_pago >= _dec(valor_total)
    esta_pago = tx_pago_total

    meio_pagamento_nome = None
    if meio_pagamento_rel is not None:
        display_fn = getattr(meio_pagamento_rel, "display", None)
        if callable(display_fn):
            try:
                meio_pagamento_nome = display_fn()
            except Exception:
                meio_pagamento_nome = (
                    getattr(meio_pagamento_rel, "nome", None)
                    or getattr(meio_pagamento_rel, "descricao", None)
                )
        else:
            meio_pagamento_nome = (
                getattr(meio_pagamento_rel, "nome", None)
                or getattr(meio_pagamento_rel, "descricao", None)
            )

    return PedidoPagamentoResumo(
        status=status,
        esta_pago=esta_pago,
        valor=valor,
        atualizado_em=atualizado_em,
        meio_pagamento_id=meio_pagamento_id,
        meio_pagamento_nome=meio_pagamento_nome,
        metodo=metodo,
        gateway=gateway,
        provider_transaction_id=provider_transaction_id,
    )


def is_pix_online_meio_pagamento(meio_pagamento) -> bool:
    """Verifica se o meio de pagamento é PIX online."""
    if not meio_pagamento:
        return False

    from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum

    meio_tipo = getattr(meio_pagamento, "tipo", None)
    if isinstance(meio_tipo, MeioPagamentoTipoEnum):
        return meio_tipo == MeioPagamentoTipoEnum.PIX_ONLINE

    if isinstance(meio_pagamento, dict):
        return meio_pagamento.get("tipo") == MeioPagamentoTipoEnum.PIX_ONLINE

    return meio_tipo == "PIX_ONLINE"


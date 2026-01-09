from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.api.cardapio.models.model_pedido_dv import PedidoDeliveryModel
from app.api.cardapio.schemas.schema_pedido import PedidoPagamentoResumo
from app.api.cadastros.schemas.schema_shared_enums import (
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
)


def _dec(value: float | Decimal | int) -> Decimal:
    """Converte valor para Decimal com precisão de 2 casas decimais."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _safe_enum(enum_cls, value):
    """Safely converte um valor para um enum, retornando None se inválido."""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def build_pagamento_resumo(pedido: PedidoDeliveryModel) -> PedidoPagamentoResumo | None:
    """Constrói resumo de pagamento a partir do pedido."""
    transacao = getattr(pedido, "transacao", None)

    meio_pagamento_rel = None
    meio_pagamento_id = None

    if transacao and getattr(transacao, "meio_pagamento", None):
        meio_pagamento_rel = transacao.meio_pagamento
        meio_pagamento_id = getattr(transacao, "meio_pagamento_id", None)
    else:
        meio_pagamento_rel = getattr(pedido, "meio_pagamento", None)
        meio_pagamento_id = getattr(pedido, "meio_pagamento_id", None)

    if not transacao and meio_pagamento_rel is None and meio_pagamento_id is None:
        return None

    status = None
    metodo = None
    gateway = None
    provider_transaction_id = None
    valor = float(pedido.valor_total or 0)
    atualizado_em = getattr(pedido, "data_atualizacao", None)

    if transacao:
        status = _safe_enum(PagamentoStatusEnum, getattr(transacao, "status", None))
        metodo = _safe_enum(PagamentoMetodoEnum, getattr(transacao, "metodo", None))
        gateway = _safe_enum(PagamentoGatewayEnum, getattr(transacao, "gateway", None))
        provider_transaction_id = getattr(transacao, "provider_transaction_id", None)

        if getattr(transacao, "valor", None) is not None:
            valor = float(transacao.valor)

        atualizado_em = (
            getattr(transacao, "pago_em", None)
            or getattr(transacao, "autorizado_em", None)
            or getattr(transacao, "cancelado_em", None)
            or getattr(transacao, "estornado_em", None)
            or getattr(transacao, "updated_at", None)
            or getattr(transacao, "created_at", None)
        )

    esta_pago = status in {PagamentoStatusEnum.PAGO, PagamentoStatusEnum.AUTORIZADO} if status else False

    meio_pagamento_nome = None
    if meio_pagamento_rel is not None:
        display_fn = getattr(meio_pagamento_rel, "display", None)
        if callable(display_fn):
            try:
                meio_pagamento_nome = display_fn()
            except Exception:
                meio_pagamento_nome = getattr(meio_pagamento_rel, "descricao", None)
        else:
            meio_pagamento_nome = getattr(meio_pagamento_rel, "descricao", None)

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


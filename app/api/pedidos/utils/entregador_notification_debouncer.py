from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Dict, Set, Tuple

logger = logging.getLogger(__name__)

# Janela para agrupar múltiplas vinculações/atualizações antes de notificar.
# Objetivo: evitar spam/duplicidade quando o admin vincula o mesmo entregador
# a vários pedidos em sequência.
DEFAULT_DEBOUNCE_SECONDS = 30


@dataclass
class _Bucket:
    timer: threading.Timer
    pedido_ids: Set[int]


_lock = threading.Lock()
_buckets: Dict[Tuple[int, int], _Bucket] = {}  # (empresa_id, entregador_id) -> bucket


def schedule_entregador_rotas_notification(
    *,
    empresa_id: int,
    entregador_id: int,
    pedido_id: int,
    debounce_seconds: int = DEFAULT_DEBOUNCE_SECONDS,
) -> None:
    """
    Agenda (com debounce) o envio de notificação de rotas para um entregador.

    - Se várias chamadas ocorrerem dentro da janela, enviamos **uma** notificação no final.
    - Também acumulamos `pedido_id`s para garantir que os pedidos recém-vinculados
      (que ainda não estejam em status "Saiu para entrega") não sejam perdidos.
    """
    key = (int(empresa_id), int(entregador_id))

    def _fire():
        with _lock:
            bucket = _buckets.pop(key, None)
        if not bucket:
            return

        pedido_ids = list(bucket.pedido_ids)
        try:
            from app.database.db_connection import SessionLocal
            from app.api.pedidos.services.service_pedido import PedidoService

            with SessionLocal() as db:
                service = PedidoService(db)
                # Usa qualquer pedido do bucket como "âncora" para empresa/config.
                anchor_id = pedido_ids[-1] if pedido_ids else int(pedido_id)
                anchor_pedido = service.repo.get_pedido(anchor_id)
                if not anchor_pedido:
                    logger.warning(
                        "[EntregadorDebounce] Pedido âncora não encontrado. key=%s anchor_id=%s",
                        key,
                        anchor_id,
                    )
                    return

                extra_pedidos = []
                if pedido_ids:
                    for pid in pedido_ids:
                        if pid == anchor_id:
                            continue
                        pedido = service.repo.get_pedido(pid)
                        if pedido:
                            extra_pedidos.append(pedido)

                service._notificar_entregador_rotas(anchor_pedido, extra_pedidos=extra_pedidos)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[EntregadorDebounce] Falha ao disparar notificação de rotas. key=%s error=%s",
                key,
                exc,
                exc_info=True,
            )

    with _lock:
        existing = _buckets.get(key)
        if existing:
            existing.pedido_ids.add(int(pedido_id))
            try:
                existing.timer.cancel()
            except Exception:
                pass
        else:
            # Bucket inicial
            existing = _Bucket(timer=threading.Timer(0, lambda: None), pedido_ids={int(pedido_id)})

        timer = threading.Timer(float(debounce_seconds), _fire)
        timer.daemon = True
        existing.timer = timer
        _buckets[key] = existing
        timer.start()


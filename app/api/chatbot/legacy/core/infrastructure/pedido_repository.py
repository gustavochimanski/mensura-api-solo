"""
Repository de Pedido (Infrastructure).

Hoje o fluxo “oficial” salva via endpoint /checkout (HTTP) e este repository ainda não é usado.
Este arquivo é um *skeleton* para futura persistência local/consulta/cancelamento por DB.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session


class PedidoRepository:
    def __init__(self, db: Session, *, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def salvar(self, payload: Dict[str, Any]) -> Optional[int]:
        """
        Skeleton: persistir pedido diretamente no banco, se/quando necessário.
        """
        raise NotImplementedError("PedidoRepository.salvar ainda não foi implementado.")

    def cancelar(self, pedido_id: int) -> bool:
        raise NotImplementedError("PedidoRepository.cancelar ainda não foi implementado.")

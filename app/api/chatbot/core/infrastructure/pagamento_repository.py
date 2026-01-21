"""
Repository de Pagamento (Infrastructure).

Responsável por buscar meios de pagamento no banco e aplicar fallback.
Implementação baseada no comportamento atual do `GroqSalesHandler._buscar_meios_pagamento`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class PagamentoRepository:
    def __init__(self, db: Session):
        self.db = db
        self._cache: Optional[List[Dict[str, Any]]] = None

    def buscar_meios_pagamento_ativos(self, *, use_cache: bool = True) -> List[Dict[str, Any]]:
        if use_cache and self._cache is not None:
            return self._cache

        try:
            result = self.db.execute(
                text(
                    """
                    SELECT id, nome, tipo
                    FROM cadastros.meios_pagamento
                    WHERE ativo = true
                    ORDER BY id
                    """
                )
            )
            meios: List[Dict[str, Any]] = [
                {"id": row[0], "nome": row[1], "tipo": row[2]} for row in result.fetchall()
            ]

            if not meios:
                meios = [
                    {"id": 1, "nome": "PIX", "tipo": "PIX_ENTREGA"},
                    {"id": 2, "nome": "Dinheiro", "tipo": "DINHEIRO"},
                    {"id": 3, "nome": "Cartão", "tipo": "CARTAO_ENTREGA"},
                ]

            self._cache = meios
            return meios
        except Exception:
            return [
                {"id": 1, "nome": "PIX", "tipo": "PIX_ENTREGA"},
                {"id": 2, "nome": "Dinheiro", "tipo": "DINHEIRO"},
                {"id": 3, "nome": "Cartão", "tipo": "CARTAO_ENTREGA"},
            ]

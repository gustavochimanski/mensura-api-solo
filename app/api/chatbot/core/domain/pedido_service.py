"""
Domain Service de Pedido.

Responsável por regras de negócio relacionadas a fechamento de pedido no fluxo do chatbot
(montagem de resumo, preview, cancelamento, etc).

Neste momento, este módulo é um *skeleton* para permitir migração incremental por delegação.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PedidoPreview:
    subtotal: float
    taxa_entrega: float
    total: float


class PedidoDomainService:
    """
    Regras de pedido/checkout que não deveriam ficar no handler.
    """

    def __init__(self, *, empresa_id: int):
        self.empresa_id = empresa_id

    def gerar_preview(self, *, carrinho: List[Dict[str, Any]], tipo_entrega: str) -> Optional[PedidoPreview]:
        """
        Calcula subtotal/taxa/total a partir do carrinho no estado da conversa.

        OBS: mantém lógica simples (igual ao handler atual); cálculo de taxa por distância
        pode ser introduzido depois via gateway/serviço de logística.
        """
        if not carrinho:
            return None

        subtotal = 0.0
        for item in carrinho:
            preco = float(item.get("preco", 0.0) or 0.0)
            qtd = int(item.get("quantidade", 1) or 1)
            preco_adicionais = float(
                (item.get("personalizacoes") or {}).get("preco_adicionais", 0.0) or 0.0
            )
            subtotal += (preco + preco_adicionais) * max(qtd, 1)

        if (tipo_entrega or "").upper() == "RETIRADA":
            taxa_entrega = 0.0
        else:
            taxa_entrega = 5.0  # TODO: calcular por distância/região

        total = subtotal + taxa_entrega
        return PedidoPreview(subtotal=subtotal, taxa_entrega=taxa_entrega, total=total)

    def validar_carrinho_nao_vazio(self, carrinho: List[Dict[str, Any]]) -> bool:
        return bool(carrinho)

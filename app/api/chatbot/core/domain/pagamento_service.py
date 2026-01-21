"""
Domain Service de Pagamento.

Responsável por regras de negócio relacionadas a escolha/validação de meios de pagamento
no fluxo do chatbot.

Neste momento, este módulo é um *skeleton* para permitir migração incremental por delegação.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PagamentoDomainService:
    def __init__(self, *, empresa_id: int):
        self.empresa_id = empresa_id

    @staticmethod
    def formatar_mensagem_formas_pagamento(meios: List[Dict[str, Any]]) -> str:
        """
        Formata a mensagem de formas de pagamento a partir de uma lista de meios.

        A obtenção dos meios (DB/cache) deve ficar em infrastructure (repository).
        """
        emoji_por_tipo = {
            "PIX_ENTREGA": "📱",
            "PIX_ONLINE": "📱",
            "DINHEIRO": "💵",
            "CARTAO_ENTREGA": "💳",
            "OUTROS": "💰",
        }

        numeros_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        mensagem = "💳 *FORMA DE PAGAMENTO*\n"
        mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
        mensagem += "Como você prefere pagar?\n\n"

        for i, meio in enumerate(meios or []):
            nome = (meio or {}).get("nome", "")
            tipo = (meio or {}).get("tipo", "OUTROS")
            emoji_num = numeros_emoji[i] if i < len(numeros_emoji) else f"{i + 1}."
            emoji_tipo = emoji_por_tipo.get(tipo, "💰")
            mensagem += f"{emoji_num} {emoji_tipo} *{nome}*\n"

        mensagem += "\n━━━━━━━━━━━━━━━━━━━━\n"
        mensagem += "Digite o *número* ou o *nome* da forma de pagamento 😊"
        return mensagem

    @staticmethod
    def selecionar_meio_por_numero(meios: List[Dict[str, Any]], numero: int) -> Optional[Dict[str, Any]]:
        if not meios:
            return None
        if not numero:
            return None
        if 1 <= numero <= len(meios):
            return meios[numero - 1]
        return None

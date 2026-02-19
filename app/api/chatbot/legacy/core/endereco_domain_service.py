"""
Domain Service de Endereço/Entrega.

Responsável por regras e fluxo de endereços (salvos / Google / complemento) e
pela transição do fluxo ENTREGA/RETIRADA para PAGAMENTO/RESUMO.

Neste momento, este módulo é um *skeleton* para permitir migração incremental por delegação.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class EnderecoDomainService:
    def __init__(self, *, empresa_id: int):
        self.empresa_id = empresa_id

    @staticmethod
    def montar_mensagem_lista_enderecos(enderecos: List[Dict[str, Any]], texto_lista: str) -> str:
        """
        Monta mensagem para seleção de endereços salvos.

        `texto_lista` normalmente vem de `ChatbotAddressService.formatar_lista_enderecos_para_chat`.
        """
        mensagem = "📍 *ENDEREÇO DE ENTREGA*\n"
        mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
        mensagem += "Você tem endereços salvos:\n\n"
        mensagem += texto_lista or ""
        mensagem += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        mensagem += "📌 Digite o *número* do endereço (ex: 1, 2, 3...)\n"
        mensagem += "🆕 Ou digite *NOVO* para cadastrar outro endereço"
        return mensagem

    @staticmethod
    def montar_mensagem_pedir_endereco() -> str:
        mensagem = "📍 *ENDEREÇO DE ENTREGA*\n"
        mensagem += "━━━━━━━━━━━━━━━━━━━━\n\n"
        mensagem += "Para onde vamos entregar?\n\n"
        mensagem += "Digite seu endereço completo:\n"
        mensagem += "• Rua e número\n"
        mensagem += "• Bairro\n"
        mensagem += "• Cidade\n\n"
        mensagem += "_Exemplo: Rua das Flores 123 Centro Brasília_"
        return mensagem

    @staticmethod
    def montar_mensagem_opcoes_google(enderecos_google: List[Dict[str, Any]]) -> str:
        mensagem = "🔍 *Encontrei esses endereços:*\n\n"
        for end in enderecos_google or []:
            mensagem += f"*{end.get('index')}.* {end.get('endereco_completo')}\n\n"
        mensagem += "📌 *É um desses?* Digite o número (1, 2 ou 3)\n"
        mensagem += "❌ Ou digite *NAO* para digitar outro endereço"
        return mensagem

    @staticmethod
    def montar_mensagem_pedir_complemento(endereco_completo: str) -> str:
        return (
            f"✅ Endereço: *{endereco_completo}*\n\n"
            "Tem algum *complemento*?\n"
            "_Ex: Apartamento 101, Bloco B, Casa dos fundos_\n\n"
            "Se não tiver, digite *NAO*"
        )

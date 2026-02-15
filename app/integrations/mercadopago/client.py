from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx


@dataclass(slots=True)
class MercadoPagoPayment:
    """Representa uma resposta simplificada de pagamento PIX do Mercado Pago."""

    id: str
    status: str
    status_detail: str | None
    qr_code: str | None
    qr_code_base64: str | None
    raw: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MercadoPagoPayment":
        point_of_interaction = data.get("point_of_interaction", {}) or {}
        transaction_data = point_of_interaction.get("transaction_data", {}) or {}

        qr_code = transaction_data.get("qr_code")
        qr_code_base64 = transaction_data.get("qr_code_base64")

        # Algumas respostas trazem o QR como imagem binária base64.
        if isinstance(qr_code_base64, dict) and "data" in qr_code_base64:
            qr_code_base64 = qr_code_base64.get("data")

        return cls(
            id=str(data.get("id")),
            status=data.get("status", "pending"),
            status_detail=data.get("status_detail"),
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
            raw=data,
        )


class MercadoPagoClient:
    """Cliente HTTP simples para acessar a API do Mercado Pago."""

    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.mercadopago.com",
        timeout: int = 20,
    ) -> None:
        if not access_token:
            raise ValueError("access_token é obrigatório para o Mercado Pago")

        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_or_get_pix_payment(
        self,
        *,
        external_reference: str,
        amount: Decimal,
        metadata: Dict[str, Any] | None = None,
        descricao: str | None = None,
        customer: Dict[str, Any] | None = None,
        existing_payment_id: str | None = None,
    ) -> MercadoPagoPayment:
        """
        Cria (ou reusa) um pagamento PIX Online.

        - `external_reference` deve ser único para o pedido (ex.: ID do pedido).
        - Se `existing_payment_id` for informado, o pagamento é consultado.
        - Caso contrário, é criado um novo via endpoint `/v1/payments`.
        """

        if existing_payment_id:
            return await self.get_payment(existing_payment_id)

        payload: Dict[str, Any] = {
            "transaction_amount": float(amount),
            "description": descricao or f"Pedido {external_reference}",
            "payment_method_id": "pix",
            "external_reference": external_reference,
            "metadata": metadata or {},
        }

        if customer:
            payload["payer"] = customer

        resp = await self._client.post("/v1/payments", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return MercadoPagoPayment.from_dict(data)

    async def get_payment(self, payment_id: str) -> MercadoPagoPayment:
        resp = await self._client.get(f"/v1/payments/{payment_id}")
        resp.raise_for_status()
        return MercadoPagoPayment.from_dict(resp.json())

    async def refund_payment(self, payment_id: str) -> MercadoPagoPayment:
        """
        Solicita reembolso (refund) do pagamento e retorna o pagamento atualizado.
        Usa o endpoint de refunds do Mercado Pago e em seguida busca o pagamento
        para obter o status atualizado.
        """
        resp = await self._client.post(f"/v1/payments/{payment_id}/refunds")
        resp.raise_for_status()
        # Após criar o refund, obtém o pagamento atualizado para refletir o novo status.
        return await self.get_payment(payment_id)


from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any

from app.api.cadastros.schemas.schema_shared_enums import (
    PagamentoStatusEnum,
    PagamentoMetodoEnum,
    PagamentoGatewayEnum,
)
from app.config import settings
from app.integrations.mercadopago.client import MercadoPagoClient, MercadoPagoPayment


@dataclass
class PaymentResult:
    status: PagamentoStatusEnum
    provider_transaction_id: str
    payload: Dict[str, Any]
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None


class PaymentGatewayClient:
    """Abstrai os diferentes gateways de pagamento usados pelo delivery."""

    def __init__(
        self,
        mode: str | None = None,
        mock_scenario: str = "success",
        mercadopago_client: MercadoPagoClient | None = None,
    ):
        self.mode = (mode or os.getenv("GATEWAY_MODE", "mock")).lower()
        self.mock_scenario = mock_scenario  # "success", "failure", "pending"
        self._mercadopago_client = mercadopago_client

    @property
    def mercadopago(self) -> MercadoPagoClient:
        if not self._mercadopago_client:
            if not settings.MERCADOPAGO_ACCESS_TOKEN:
                raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN não configurado")
            self._mercadopago_client = MercadoPagoClient(
                access_token=settings.MERCADOPAGO_ACCESS_TOKEN,
                base_url=settings.MERCADOPAGO_BASE_URL,
                timeout=settings.MERCADOPAGO_TIMEOUT_SECONDS,
            )
        return self._mercadopago_client

    async def charge(
        self,
        *,
        order_id: int,
        amount: Decimal,
        metodo: PagamentoMetodoEnum,
        gateway: PagamentoGatewayEnum,
        metadata: Dict[str, Any] | None = None,
        descricao: str | None = None,
        customer: Dict[str, Any] | None = None,
        existing_payment_id: str | None = None,
    ) -> PaymentResult:
        metadata = metadata or {}

        if gateway == PagamentoGatewayEnum.MERCADOPAGO:
            return await self._charge_mercadopago(
                order_id=order_id,
                amount=amount,
                metodo=metodo,
                metadata=metadata,
                descricao=descricao,
                customer=customer,
                existing_payment_id=existing_payment_id,
            )

        if self.mode == "mock":
            return self._mock_charge(
                order_id=order_id,
                amount=amount,
                metodo=metodo,
                gateway=gateway,
                metadata=metadata,
            )

        raise RuntimeError("Gateway real não suportado para o modo atual")

    async def consult(
        self,
        *,
        gateway: PagamentoGatewayEnum,
        payment_id: str,
    ) -> PaymentResult:
        if gateway == PagamentoGatewayEnum.MERCADOPAGO:
            payment = await self.mercadopago.get_payment(payment_id)
            return self._payment_to_result(payment)

        raise RuntimeError(f"Consulta não implementada para gateway {gateway}")

    async def _charge_mercadopago(
        self,
        *,
        order_id: int,
        amount: Decimal,
        metodo: PagamentoMetodoEnum,
        metadata: Dict[str, Any],
        descricao: str | None,
        customer: Dict[str, Any] | None,
        existing_payment_id: str | None,
    ) -> PaymentResult:
        if metodo != PagamentoMetodoEnum.PIX_ONLINE:
            raise RuntimeError("Mercado Pago integrado somente para PIX_ONLINE")

        payment = await self.mercadopago.create_or_get_pix_payment(
            external_reference=str(order_id),
            amount=amount,
            metadata=metadata,
            descricao=descricao,
            customer=customer,
            existing_payment_id=existing_payment_id,
        )
        return self._payment_to_result(payment)

    def _mock_charge(
        self,
        *,
        order_id: int,
        amount: Decimal,
        metodo: PagamentoMetodoEnum,
        gateway: PagamentoGatewayEnum,
        metadata: Dict[str, Any],
    ) -> PaymentResult:
        if self.mock_scenario == "failure":
            status = PagamentoStatusEnum.RECUSADO
        elif self.mock_scenario == "pending":
            status = PagamentoStatusEnum.PENDENTE
        else:
            status = PagamentoStatusEnum.PAGO

        provider_id = f"mock_{metodo.value.lower()}_{uuid.uuid4().hex[:10]}"

        payload = {
            "mock": True,
            "order_id": order_id,
            "amount": str(amount),
            "metodo": metodo.value,
            "gateway": gateway.value,
            "metadata": metadata,
        }

        qr_code = None
        qr_code_base64 = None
        if metodo == PagamentoMetodoEnum.PIX_ONLINE and status == PagamentoStatusEnum.PAGO:
            qr_code = "00020126580014BR.GOV.BCB.PIX***"  # valor fictício
            qr_code_base64 = "iVBORw0K***"  # base64 fictício

        return PaymentResult(
            status=status,
            provider_transaction_id=provider_id,
            payload=payload,
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
        )

    def _payment_to_result(self, payment: MercadoPagoPayment) -> PaymentResult:
        status_map = {
            "pending": PagamentoStatusEnum.PENDENTE,
            "in_process": PagamentoStatusEnum.PENDENTE,
            "authorized": PagamentoStatusEnum.AUTORIZADO,
            "approved": PagamentoStatusEnum.PAGO,
            "rejected": PagamentoStatusEnum.RECUSADO,
            "cancelled": PagamentoStatusEnum.CANCELADO,
            "refunded": PagamentoStatusEnum.ESTORNADO,
            "charged_back": PagamentoStatusEnum.ESTORNADO,
        }

        status = status_map.get(payment.status, PagamentoStatusEnum.PENDENTE)

        return PaymentResult(
            status=status,
            provider_transaction_id=payment.id,
            payload=payment.raw,
            qr_code=payment.qr_code,
            qr_code_base64=payment.qr_code_base64,
        )

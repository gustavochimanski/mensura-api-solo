from __future__ import annotations
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any

from app.api.delivery.schemas.shared_enums import PagamentoStatusEnum, PagamentoMetodoEnum, PagamentoGatewayEnum

@dataclass
class PaymentResult:
    status: PagamentoStatusEnum
    provider_transaction_id: str
    payload: Dict[str, Any]
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None

class PaymentGatewayClient:
    """
    Abstrai o gateway. Em produção, implemente aqui chamadas HTTP (httpx) para o provedor.
    Em dev, usamos o modo MOCK (default) que sempre retorna sucesso.
    """
    def __init__(self, mode: str | None = None):
        self.mode = (mode or os.getenv("GATEWAY_MODE", "mock")).lower()

    async def charge(
        self,
        *,
        order_id: int,
        amount: Decimal,
        metodo: PagamentoMetodoEnum,
        gateway: PagamentoGatewayEnum,
        metadata: Dict[str, Any] | None = None,
    ) -> PaymentResult:
        if self.mode == "mock":
            # Simula sucesso do provedor
            return PaymentResult(
                status=PagamentoStatusEnum.PAGO,
                provider_transaction_id=f"mock_{uuid.uuid4().hex[:16]}",
                payload={"mock": True, "order_id": order_id, "amount": str(amount), "metodo": metodo.value},
                qr_code="00020126580014BR.GOV.BCB.PIX...",  # exemplo de 'copia e cola'
                qr_code_base64=None,
            )

        # Exemplo para quando integrar com um gateway real:
        # async with httpx.AsyncClient(timeout=15) as client:
        #     resp = await client.post("https://gateway/charge", json={...})
        #     resp.raise_for_status()
        #     data = resp.json()
        #     return PaymentResult(
        #         status=PagamentoStatusEnum.PAGO if data["status"] == "approved" else PagamentoStatusEnum.RECUSADO,
        #         provider_transaction_id=data["id"],
        #         payload=data,
        #         qr_code=data.get("qr_code"),
        #         qr_code_base64=data.get("qr_code_base64"),
        #     )
        raise RuntimeError("GATEWAY_MODE != 'mock' mas integração real não implementada ainda.")

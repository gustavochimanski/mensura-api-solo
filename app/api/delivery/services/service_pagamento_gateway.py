from __future__ import annotations
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any

from app.api.delivery.schemas.schema_shared_enums import PagamentoStatusEnum, PagamentoMetodoEnum, PagamentoGatewayEnum

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
    def __init__(self, mode: str | None = None, mock_scenario: str = "success"):
        self.mode = (mode or os.getenv("GATEWAY_MODE", "mock")).lower()
        self.mock_scenario = mock_scenario  # "success", "failure", "pending"

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
            # Simula comportamento baseado no método de pagamento e cenário
            if self.mock_scenario == "failure":
                return PaymentResult(
                    status=PagamentoStatusEnum.RECUSADO,
                    provider_transaction_id=f"failed_{uuid.uuid4().hex[:12]}",
                    payload={
                        "mock": True, 
                        "order_id": order_id, 
                        "amount": str(amount), 
                        "metodo": metodo.value,
                        "gateway": gateway.value,
                        "error": "Pagamento recusado pelo gateway",
                        "metadata": metadata or {}
                    },
                    qr_code=None,
                    qr_code_base64=None,
                )
            elif self.mock_scenario == "pending":
                return PaymentResult(
                    status=PagamentoStatusEnum.PENDENTE,
                    provider_transaction_id=f"pending_{uuid.uuid4().hex[:12]}",
                    payload={
                        "mock": True, 
                        "order_id": order_id, 
                        "amount": str(amount), 
                        "metodo": metodo.value,
                        "gateway": gateway.value,
                        "metadata": metadata or {}
                    },
                    qr_code=None,
                    qr_code_base64=None,
                )
            else:  # success
                if metodo == PagamentoMetodoEnum.PIX_ONLINE:
                    # Para PIX_ONLINE, simula geração de QR Code
                    return PaymentResult(
                        status=PagamentoStatusEnum.PAGO,
                        provider_transaction_id=f"pix_online_{uuid.uuid4().hex[:16]}",
                        payload={
                            "mock": True, 
                            "order_id": order_id, 
                            "amount": str(amount), 
                            "metodo": metodo.value,
                            "gateway": gateway.value,
                            "metadata": metadata or {}
                        },
                        qr_code="00020126580014BR.GOV.BCB.PIX0136123e4567-e89b-12d3-a456-426614174000520400005303986540510.005802BR5913Teste PIX Online6008BRASILIA62070503***63041D3D",
                        qr_code_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                    )
                else:
                    # Para outros métodos, simula processamento direto
                    return PaymentResult(
                        status=PagamentoStatusEnum.PAGO,
                        provider_transaction_id=f"direct_{metodo.value}_{uuid.uuid4().hex[:12]}",
                        payload={
                            "mock": True, 
                            "order_id": order_id, 
                            "amount": str(amount), 
                            "metodo": metodo.value,
                            "gateway": gateway.value,
                            "metadata": metadata or {}
                        },
                        qr_code=None,
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

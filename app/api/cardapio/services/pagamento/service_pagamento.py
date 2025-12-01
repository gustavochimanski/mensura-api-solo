from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
from app.api.shared.schemas.schema_shared_enums import (
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
)
from app.api.cardapio.schemas.schema_transacao_pagamento import (
    TransacaoCreateRequest,
    TransacaoResponse,
    TransacaoStatusUpdateRequest,
)
from .service_pagamento_gateway import (
    PaymentGatewayClient,
    PaymentResult,
)
from app.integrations.mercadopago.client import MercadoPagoClient


@dataclass(slots=True)
class PagamentoGatewayConfig:
    mercadopago: Optional[MercadoPagoClient] = None


class PagamentoService:
    """Camada de orquestração de pagamentos (gateway + persistência)."""

    def __init__(
        self,
        db: Session,
        *,
        gateway_client: PaymentGatewayClient | None = None,
        gateway_config: PagamentoGatewayConfig | None = None,
    ) -> None:
        self.repo = PagamentoRepository(db)
        self.gateway = gateway_client or PaymentGatewayClient(
            mercadopago_client=(gateway_config.mercadopago if gateway_config else None)
        )

    # ---------------- Queries ----------------
    def get_transacao(self, pedido_id: int) -> TransacaoResponse | None:
        tx = self.repo.get_by_pedido_id(pedido_id)
        if not tx:
            return None
        return TransacaoResponse.model_validate(tx)

    # ---------------- Commands ---------------
    async def iniciar_transacao(
        self,
        *,
        pedido_id: int,
        meio_pagamento_id: int,
        valor: Decimal,
        metodo: PagamentoMetodoEnum,
        gateway: PagamentoGatewayEnum,
        moeda: str = "BRL",
        descricao: str | None = None,
        metadata: Dict[str, Any] | None = None,
        customer: Dict[str, Any] | None = None,
        existing_payment_id: str | None = None,
    ) -> TransacaoResponse:
        transacao = self.repo.criar(
            pedido_id=pedido_id,
            meio_pagamento_id=meio_pagamento_id,
            gateway=gateway.value,
            metodo=metodo.value,
            valor=valor,
            moeda=moeda,
        )

        if not self._deve_usar_gateway(metodo, gateway):
            self.repo.atualizar(
                transacao,
                status=PagamentoStatusEnum.PAGO.value,
                provider_transaction_id=f"direct_{pedido_id}_{metodo.value}",
                payload_retorno={"metodo": metodo.value, "gateway": "DIRETO"},
            )
            self.repo.registrar_evento(transacao, "pago_em")
            self.repo.commit()
            return TransacaoResponse.model_validate(transacao)

        result = await self._charge_gateway(
            order_id=pedido_id,
            amount=valor,
            metodo=metodo,
            gateway=gateway,
            metadata=metadata,
            descricao=descricao,
            customer=customer,
            existing_payment_id=existing_payment_id,
        )

        self._aplicar_resultado(transacao, result)
        self.repo.commit()
        return TransacaoResponse.model_validate(transacao)

    async def atualizar_status(
        self,
        *,
        pedido_id: int,
        payload: TransacaoStatusUpdateRequest,
    ) -> TransacaoResponse:
        transacao = self.repo.get_by_pedido_id(pedido_id)
        if not transacao:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Transação não encontrada")

        self.repo.atualizar(
            transacao,
            status=payload.status.value,
            provider_transaction_id=payload.provider_transaction_id,
            payload_retorno=payload.payload_retorno,
            qr_code=payload.qr_code,
            qr_code_base64=payload.qr_code_base64,
        )

        if payload.status == PagamentoStatusEnum.AUTORIZADO:
            self.repo.registrar_evento(transacao, "autorizado_em")
        elif payload.status == PagamentoStatusEnum.PAGO:
            self.repo.registrar_evento(transacao, "pago_em")
        elif payload.status == PagamentoStatusEnum.CANCELADO:
            self.repo.registrar_evento(transacao, "cancelado_em")
        elif payload.status == PagamentoStatusEnum.ESTORNADO:
            self.repo.registrar_evento(transacao, "estornado_em")

        self.repo.commit()
        return TransacaoResponse.model_validate(transacao)

    async def consultar_gateway(
        self,
        *,
        gateway: PagamentoGatewayEnum,
        provider_transaction_id: str,
    ) -> PaymentResult:
        return await self.gateway.consult(
            gateway=gateway,
            payment_id=provider_transaction_id,
        )

    # ---------------- Helpers -----------------
    def _deve_usar_gateway(
        self,
        metodo: PagamentoMetodoEnum,
        gateway: PagamentoGatewayEnum,
    ) -> bool:
        return metodo == PagamentoMetodoEnum.PIX_ONLINE and gateway != PagamentoGatewayEnum.MOCK

    async def _charge_gateway(
        self,
        *,
        order_id: int,
        amount: Decimal,
        metodo: PagamentoMetodoEnum,
        gateway: PagamentoGatewayEnum,
        metadata: Dict[str, Any] | None,
        descricao: str | None,
        customer: Dict[str, Any] | None,
        existing_payment_id: str | None,
    ) -> PaymentResult:
        return await self.gateway.charge(
            order_id=order_id,
            amount=amount,
            metodo=metodo,
            gateway=gateway,
            metadata=metadata,
            descricao=descricao,
            customer=customer,
            existing_payment_id=existing_payment_id,
        )

    def _aplicar_resultado(
        self,
        transacao: Any,
        result: PaymentResult,
    ) -> None:
        status_map = {
            PagamentoStatusEnum.PAGO: (PagamentoStatusEnum.PAGO.value, "pago_em"),
            PagamentoStatusEnum.AUTORIZADO: (PagamentoStatusEnum.AUTORIZADO.value, "autorizado_em"),
            PagamentoStatusEnum.PENDENTE: (PagamentoStatusEnum.PENDENTE.value, None),
            PagamentoStatusEnum.RECUSADO: (PagamentoStatusEnum.RECUSADO.value, None),
            PagamentoStatusEnum.CANCELADO: (PagamentoStatusEnum.CANCELADO.value, "cancelado_em"),
            PagamentoStatusEnum.ESTORNADO: (PagamentoStatusEnum.ESTORNADO.value, "estornado_em"),
        }

        mapped_status, timestamp_field = status_map.get(
            result.status,
            (PagamentoStatusEnum.PENDENTE.value, None),
        )

        self.repo.atualizar(
            transacao,
            status=mapped_status,
            provider_transaction_id=result.provider_transaction_id,
            payload_retorno=result.payload,
            qr_code=result.qr_code,
            qr_code_base64=result.qr_code_base64,
        )

        if timestamp_field:
            self.repo.registrar_evento(transacao, timestamp_field)


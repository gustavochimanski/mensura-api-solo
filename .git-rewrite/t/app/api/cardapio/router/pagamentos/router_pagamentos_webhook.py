from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.api.cadastros.schemas.schema_shared_enums import PagamentoGatewayEnum
from app.api.cardapio.schemas.schema_transacao_pagamento import TransacaoStatusUpdateRequest
from app.api.cardapio.services.pedidos.service_pedido import PedidoService
from app.api.cardapio.services.pedidos.dependencies import get_pedido_service
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/cardapio/public/webhooks/pagamentos",
    tags=["Public - Delivery - Mercado Pago Webhooks"],
)


class MercadoPagoWebhookPayload(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    date_created: Optional[str] = None
    user_id: Optional[str] = None
    api_version: Optional[str] = None
    live_mode: Optional[bool] = None
    data: Dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")

    def extract_payment_id(self) -> Optional[str]:
        if isinstance(self.data, dict):
            data_id = self.data.get("id") or self.data.get("resource_id")
            if data_id:
                return str(data_id)

        if self.resource:
            resource = str(self.resource).rstrip("/")
            if resource:
                parts = resource.split("/")
                if parts:
                    return parts[-1]

        return None


@router.get("/mercadopago", status_code=status.HTTP_200_OK)
async def mercadopago_webhook_healthcheck() -> Dict[str, str]:
    """Endpoint simples para verificação do Mercado Pago."""
    return {"status": "ok"}


@router.post("/mercadopago", status_code=status.HTTP_200_OK)
async def mercadopago_webhook(
    payload: MercadoPagoWebhookPayload | None = Body(None),
    payment_id_query: Optional[str] = Query(None, alias="id"),
    topic: Optional[str] = Query(None, alias="topic"),
    db: Session = Depends(get_db),
    pedido_service: PedidoService = Depends(get_pedido_service),
):
    payment_id = payment_id_query or (payload.extract_payment_id() if payload else None)

    if not payment_id:
        logger.warning("[MercadoPago][Webhook] Notificação ignorada: payment_id ausente")
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"status": "ignored", "reason": "missing_payment_id"},
        )

    logger.info(
        "[MercadoPago][Webhook] Recebido - payment_id=%s topic=%s", payment_id, topic
    )

    try:
        consulta = await pedido_service.consultar_pagamento_gateway(
            gateway=PagamentoGatewayEnum.MERCADOPAGO,
            provider_transaction_id=payment_id,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - log detalhado
        logger.exception(
            "[MercadoPago][Webhook] Falha ao consultar pagamento %s: %s",
            payment_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar o pagamento no Mercado Pago",
        )

    external_reference = None
    if isinstance(consulta.payload, dict):
        external_reference = consulta.payload.get("external_reference")

    try:
        pedido_id = int(external_reference) if external_reference is not None else None
    except (TypeError, ValueError):
        pedido_id = None

    if not pedido_id:
        logger.warning(
            "[MercadoPago][Webhook] Notificação ignorada: external_reference inválido payload=%s",
            consulta.payload,
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"status": "ignored", "reason": "missing_pedido_id"},
        )

    logger.info(
        "[MercadoPago][Webhook] Atualizando pedido_id=%s status=%s",
        pedido_id,
        consulta.status.value,
    )

    update_payload = TransacaoStatusUpdateRequest(
        status=consulta.status,
        provider_transaction_id=consulta.provider_transaction_id,
        payload_retorno=consulta.payload,
        qr_code=consulta.qr_code,
        qr_code_base64=consulta.qr_code_base64,
    )

    updated_pedido = await pedido_service.atualizar_status_pagamento(
        pedido_id=pedido_id,
        payload=update_payload,
    )

    return {
        "status": "ok",
        "pedido_id": updated_pedido.id,
        "pagamento_status": (updated_pedido.pagamento.status.value if updated_pedido.pagamento else None),
    }



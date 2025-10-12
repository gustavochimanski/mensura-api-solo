from fastapi import APIRouter, status, Path, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido import PedidoResponse
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum
from app.api.delivery.schemas.schema_transacao_pagamento import (
    ConsultarTransacaoResponse,
    TransacaoResponse,
)
from app.api.delivery.services.pedidos.service_pedido import PedidoService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/client/pagamentos", tags=["Client  Delivery - Pagamentos"], dependencies=[Depends(get_cliente_by_super_token)])


@router.post("/{pedido_id}/confirmar", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def confirmar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    metodo: PagamentoMetodoEnum = Query(default=PagamentoMetodoEnum.PIX, description="Método de pagamento"),
    gateway: PagamentoGatewayEnum = Query(default=PagamentoGatewayEnum.PIX_INTERNO, description="Gateway de pagamento"),
    db: Session = Depends(get_db),
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
):
    logger.info(
        f"[Pagamentos] Confirmar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}"
    )
    svc = PedidoService(db)
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    return await svc.confirmar_pagamento(pedido_id=pedido_id, metodo=metodo, gateway=gateway)


@router.post(
    "/{pedido_id}",
    response_model=TransacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def iniciar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    metodo: PagamentoMetodoEnum = Query(default=PagamentoMetodoEnum.PIX_ONLINE),
    gateway: PagamentoGatewayEnum = Query(default=PagamentoGatewayEnum.MERCADOPAGO),
    db: Session = Depends(get_db),
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
):
    logger.info(
        f"[Pagamentos] Iniciar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}"
    )
    svc = PedidoService(db)
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    transacao = await svc.pagamentos.iniciar_transacao(
        pedido_id=pedido.id,
        meio_pagamento_id=pedido.meio_pagamento_id,
        valor=svc._dec(pedido.valor_total),
        metodo=metodo,
        gateway=gateway,
        metadata={"pedido_id": pedido.id, "cliente_id": cliente.id},
    )
    return transacao


@router.get(
    "/{pedido_id}/{provider_id}",
    response_model=ConsultarTransacaoResponse,
    status_code=status.HTTP_200_OK,
)
async def consultar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    provider_id: str = Path(..., description="ID da transação no provedor"),
    gateway: PagamentoGatewayEnum = Query(default=PagamentoGatewayEnum.MERCADOPAGO),
    db: Session = Depends(get_db),
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
):
    logger.info(
        f"[Pagamentos] Consultar pagamento - pedido_id={pedido_id} provider_id={provider_id} gateway={gateway}"
    )
    svc = PedidoService(db)
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    result = await svc.consultar_pagamento_gateway(
        gateway=gateway,
        provider_transaction_id=provider_id,
    )
    return ConsultarTransacaoResponse(
        status=result.status,
        provider_transaction_id=result.provider_transaction_id,
        payload=result.payload,
        qr_code=result.qr_code,
        qr_code_base64=result.qr_code_base64,
    )

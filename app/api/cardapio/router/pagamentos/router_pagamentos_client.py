from fastapi import APIRouter, status, Path, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.pedidos.schemas.schema_pedido import PedidoResponse
from app.api.shared.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum
from app.api.cardapio.schemas.schema_transacao_pagamento import (
    ConsultarTransacaoResponse,
    TransacaoResponse,
)
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.dependencies import get_pedido_service
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/cardapio/client/pagamentos", tags=["Client - Cardápio - Pagamentos"], dependencies=[Depends(get_cliente_by_super_token)])


@router.post("/{pedido_id}/confirmar", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def confirmar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    metodo: PagamentoMetodoEnum = Query(default=PagamentoMetodoEnum.PIX, description="Método de pagamento"),
    gateway: PagamentoGatewayEnum = Query(default=PagamentoGatewayEnum.PIX_INTERNO, description="Gateway de pagamento"),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    [DESATIVADO] Confirma o pagamento de um pedido.

    A confirmação de pagamento (que altera o status do pedido) agora
    é permitida apenas via endpoints de admin / webhooks internos.
    """
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Confirmação de pagamento que altera status de pedido é permitida apenas em endpoints de admin.",
    )


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
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    logger.info(
        f"[Pagamentos] Iniciar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}"
    )
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    # Novo padrão: se o pedido já possui transações, evita criar duplicadas.
    txs = list(getattr(pedido, "transacoes", None) or [])
    if txs:
        if len(txs) > 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Pedido possui múltiplas transações. Inicie o pagamento usando /transacoes/{transacao_id}/iniciar.",
            )
        tx0 = txs[0]
        updated = await svc.pagamentos.iniciar_transacao(
            pedido_id=pedido.id,
            meio_pagamento_id=tx0.meio_pagamento_id,
            valor=svc._dec(tx0.valor),
            metodo=metodo,
            gateway=gateway,
            metadata={"pedido_id": pedido.id, "cliente_id": cliente.id, "transacao_id": tx0.id},
            transacao_id=tx0.id,
            existing_payment_id=getattr(tx0, "provider_transaction_id", None),
        )
        return updated

    if pedido.meio_pagamento_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Pedido sem meio de pagamento/transação. Finalize o checkout informando meios_pagamento para criar transações pendentes.",
        )

    transacao = await svc.pagamentos.iniciar_transacao(
        pedido_id=pedido.id,
        meio_pagamento_id=pedido.meio_pagamento_id,
        valor=svc._dec(pedido.valor_total),
        metodo=metodo,
        gateway=gateway,
        metadata={"pedido_id": pedido.id, "cliente_id": cliente.id},
    )
    return transacao


@router.post(
    "/transacoes/{transacao_id}/iniciar",
    response_model=TransacaoResponse,
    status_code=status.HTTP_200_OK,
)
async def iniciar_pagamento_por_transacao(
    transacao_id: int = Path(..., description="ID da transação"),
    metodo: PagamentoMetodoEnum = Query(default=PagamentoMetodoEnum.PIX_ONLINE),
    gateway: PagamentoGatewayEnum = Query(default=PagamentoGatewayEnum.MERCADOPAGO),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Inicia pagamento (gateway) para uma transação específica.

    Útil quando o pedido tem múltiplas transações (ex.: parte em PIX_ONLINE, parte em dinheiro).
    """
    tx = svc.pagamentos.get_transacao_by_id(transacao_id)
    if not tx:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transação não encontrada")

    pedido = svc.repo.get_pedido(tx.pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    # Reutiliza a transação existente (não cria duplicada)
    updated = await svc.pagamentos.iniciar_transacao(
        pedido_id=pedido.id,
        meio_pagamento_id=tx.meio_pagamento_id,
        valor=svc._dec(tx.valor),
        metodo=metodo,
        gateway=gateway,
        metadata={"pedido_id": pedido.id, "cliente_id": cliente.id, "transacao_id": transacao_id},
        transacao_id=transacao_id,
        existing_payment_id=tx.provider_transaction_id,
    )
    return updated


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
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    logger.info(
        f"[Pagamentos] Consultar pagamento - pedido_id={pedido_id} provider_id={provider_id} gateway={gateway}"
    )
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

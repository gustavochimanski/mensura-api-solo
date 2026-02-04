from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.orm import Session

from app.api.pedidos.schemas.schema_pedido import PedidoResponse
from app.api.cardapio.schemas.schema_transacao_pagamento import TransacaoStatusUpdateRequest
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.dependencies import get_pedido_service
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/cardapio/admin/pagamentos", tags=["Admin - Cardápio - Pagamentos"], dependencies=[Depends(get_current_user)])


@router.post(
    "/{pedido_id}/status",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
async def atualizar_status_pagamento(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: TransacaoStatusUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Atualiza o status do pagamento a partir de um evento externo (webhook/admin)."""
    logger.info(
        f"[Pagamentos][Admin] Atualizar status pagamento - pedido_id={pedido_id} status={payload.status}"
    )

    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    return await svc.atualizar_status_pagamento(pedido_id=pedido_id, payload=payload)


@router.post(
    "/transacoes/{transacao_id}/status",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
async def atualizar_status_pagamento_por_transacao(
    transacao_id: int = Path(..., description="ID da transação", gt=0),
    payload: TransacaoStatusUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Atualiza o status de uma transação específica (novo padrão).

    Necessário quando o pedido possui múltiplas transações.
    """
    logger.info(
        f"[Pagamentos][Admin] Atualizar status transacao - transacao_id={transacao_id} status={payload.status}"
    )
    return await svc.atualizar_status_pagamento_por_transacao_id(transacao_id=transacao_id, payload=payload)

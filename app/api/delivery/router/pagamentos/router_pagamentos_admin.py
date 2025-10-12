from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.orm import Session

from app.api.delivery.schemas.schema_pedido import PedidoResponse
from app.api.delivery.schemas.schema_transacao_pagamento import TransacaoStatusUpdateRequest
from app.api.delivery.services.pedidos.service_pedido import PedidoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/admin/pagamentos", tags=[" Admin - Delivery - Pagamentos"], dependencies=[Depends(get_current_user)])


@router.post(
    "/{pedido_id}/status",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
async def atualizar_status_pagamento(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: TransacaoStatusUpdateRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Atualiza o status do pagamento a partir de um evento externo (webhook/admin)."""
    logger.info(
        f"[Pagamentos][Admin] Atualizar status pagamento - pedido_id={pedido_id} status={payload.status}"
    )

    svc = PedidoService(db)
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    return await svc.atualizar_status_pagamento(pedido_id=pedido_id, payload=payload)

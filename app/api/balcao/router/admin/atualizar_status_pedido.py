from fastapi import APIRouter, Depends, Path, status, Body
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
    AtualizarStatusPedidoRequest,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service
from app.api.cadastros.models.user_model import UserModel


router = APIRouter(
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.patch(
    "/{pedido_id:int}/status",
    response_model=PedidoBalcaoOut,
    summary="Atualizar status do pedido",
    description="""
    Atualiza manualmente o status de um pedido de balcão.

    **Observações:**
    - Para definir status ENTREGUE ou CANCELADO utilize esta rota ou as operações específicas.
    """
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AtualizarStatusPedidoRequest = Body(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Atualiza o status de um pedido de balcão"""
    return svc.atualizar_status(pedido_id, body, usuario_id=current_user.id)


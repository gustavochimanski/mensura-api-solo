from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    RemoverItemResponse,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service
from app.api.cadastros.models.user_model import UserModel


router = APIRouter(
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.delete(
    "/{pedido_id:int}/itens/{item_id:int}",
    response_model=RemoverItemResponse,
    summary="Remover item do pedido",
    description="""
    Remove um item específico do pedido de balcão.
    
    **Validações:**
    - Pedido deve estar aberto (não pode ser CANCELADO ou ENTREGUE)
    - Item deve existir no pedido
    
    **Atualização automática:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Item removido com sucesso"},
        400: {"description": "Pedido fechado/cancelado"},
        404: {"description": "Pedido ou item não encontrado"}
    }
)
def remover_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item_id: int = Path(..., description="ID do item a ser removido", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Remove um item do pedido de balcão"""
    return svc.remover_item(pedido_id, item_id, usuario_id=current_user.id)


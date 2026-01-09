from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service
from app.api.cadastros.models.user_model import UserModel


router = APIRouter(
    prefix="/api/balcao/admin/pedidos",
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/{pedido_id:int}/confirmar",
    response_model=PedidoBalcaoOut,
    summary="Confirmar pedido",
    description="""
    Confirma um pedido de balcão, alterando seu status de PENDENTE para EM IMPRESSÃO.
    
    **Fluxo de status (sem o estágio 'Saiu para entrega'):**
    - PENDENTE → EM IMPRESSÃO → EM PREPARO → ENTREGUE
    
    **Observação:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Pedido confirmado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def confirmar_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser confirmado", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Confirma um pedido de balcão"""
    return svc.confirmar(pedido_id, usuario_id=current_user.id)


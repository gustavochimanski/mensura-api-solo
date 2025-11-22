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
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/{pedido_id:int}/abrir",
    response_model=PedidoBalcaoOut,
    summary="Abrir pedido",
    description="""
    Atalho para reabrir um pedido de balcão que foi encerrado (ENTREGUE ou CANCELADO).
    
    O pedido volta para o fluxo de produção (status CONFIRMADO/EM IMPRESSÃO).
    """,
    responses={
        200: {"description": "Pedido aberto com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def abrir_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser reaberto", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Reabre um pedido de balcão (atalho para /reabrir)."""
    return svc.reabrir(pedido_id, usuario_id=current_user.id)


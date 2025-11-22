from fastapi import APIRouter, Depends, Path, status, Body
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
    FecharContaBalcaoRequest,
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
    "/{pedido_id:int}/fechar",
    response_model=PedidoBalcaoOut,
    summary="Fechar pedido",
    description="""
    Atalho para fechar a conta de um pedido de balcão, alterando o status para ENTREGUE.

    Aceita as mesmas informações de pagamento opcionais do endpoint `/fechar-conta`.
    """,
    responses={
        200: {"description": "Pedido fechado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def fechar_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser fechado", gt=0),
    payload: FecharContaBalcaoRequest | None = Body(
        default=None,
        description="Dados de pagamento (opcional)"
    ),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Fecha a conta de um pedido de balcão (atalho)."""
    return svc.fechar_conta(pedido_id, payload, usuario_id=current_user.id)


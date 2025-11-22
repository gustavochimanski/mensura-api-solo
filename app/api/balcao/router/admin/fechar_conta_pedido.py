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
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/{pedido_id:int}/fechar-conta",
    response_model=PedidoBalcaoOut,
    summary="Fechar conta do pedido",
    description="""
    Fecha a conta de um pedido de balcão, alterando seu status para ENTREGUE.
    
    **Informações de pagamento (opcional):**
    - `meio_pagamento_id`: ID do meio de pagamento utilizado
    - `troco_para`: Valor para o qual deseja troco (apenas para pagamento em dinheiro)
    
    **Observação:** As informações de pagamento são salvas nas observações do pedido.
    """,
    responses={
        200: {"description": "Conta fechada com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def fechar_conta_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: FecharContaBalcaoRequest | None = Body(
        default=None,
        description="Dados de pagamento (opcional)"
    ),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Fecha a conta de um pedido de balcão"""
    return svc.fechar_conta(pedido_id, payload, usuario_id=current_user.id)


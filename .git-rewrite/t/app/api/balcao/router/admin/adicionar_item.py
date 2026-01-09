from fastapi import APIRouter, Depends, Path, status, Body
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
    AdicionarItemRequest,
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
    "/{pedido_id:int}/itens",
    response_model=PedidoBalcaoOut,
    summary="Adicionar item ao pedido (LEGADO - Use /produtos)",
    description="""
    ⚠️ **LEGADO**: Use o endpoint `/produtos` que aceita produtos, receitas e combos.
    
    Adiciona um novo item (produto normal) ao pedido de balcão.
    
    **Validações:**
    - Pedido deve estar aberto (não pode ser CANCELADO ou ENTREGUE)
    - Produto deve existir e estar disponível
    - Quantidade deve ser maior que zero
    
    **Atualização automática:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Item adicionado com sucesso"},
        400: {"description": "Pedido fechado/cancelado ou dados inválidos"},
        404: {"description": "Pedido ou produto não encontrado"}
    }
)
def adicionar_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarItemRequest = Body(..., description="Dados do item a ser adicionado"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Adiciona um item ao pedido de balcão"""
    return svc.adicionar_item(pedido_id, body, usuario_id=current_user.id)


from fastapi import APIRouter, Depends, Path, status, Body
from sqlalchemy.orm import Session

from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
    FecharContaBalcaoRequest,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.cadastros.models.model_cliente_dv import ClienteModel


router = APIRouter(
    prefix="/api/balcao/client/pedidos",
    tags=["Client - Balcão - Pedidos"],
)


@router.post(
    "/{pedido_id}/fechar-conta",
    response_model=PedidoBalcaoOut,
    status_code=status.HTTP_200_OK,
    summary="Fechar conta do pedido (Cliente)",
    description="""
    Permite que um cliente feche a conta de seu próprio pedido de balcão.
    
    **Autenticação:** Requer header `X-Super-Token` com o token do cliente.
    
    **Validações:**
    - Cliente deve ser o dono do pedido (se pedido tiver cliente_id associado)
    - Pedido deve existir
    
    **Informações de pagamento:**
    - `meio_pagamento_id`: ID do meio de pagamento utilizado (opcional)
    - `troco_para`: Valor para o qual deseja troco, apenas para pagamento em dinheiro (opcional)
    
    **Observação:** As informações de pagamento são salvas nas observações do pedido.
    O status do pedido é alterado para ENTREGUE.
    """,
    responses={
        200: {"description": "Conta fechada com sucesso"},
        401: {"description": "Não autenticado. Requer X-Super-Token"},
        403: {"description": "Pedido não pertence ao cliente"},
        404: {"description": "Pedido não encontrado"}
    }
)
def fechar_conta_pedido_cliente(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: FecharContaBalcaoRequest = Body(..., description="Dados de pagamento"),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """Permite que um cliente feche a conta de seu pedido de balcão"""
    svc = PedidoBalcaoService(db)
    return svc.fechar_conta_cliente(pedido_id, cliente.id, payload)



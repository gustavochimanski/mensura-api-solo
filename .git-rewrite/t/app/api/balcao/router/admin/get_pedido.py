from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service


router = APIRouter(
    prefix="/api/balcao/admin/pedidos",
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/{pedido_id:int}",
    response_model=PedidoBalcaoOut,
    summary="Buscar pedido por ID",
    description="""
    Busca um pedido de balcão específico pelo ID.
    
    **Retorna:**
    - Informações completas do pedido
    - Lista de itens do pedido
    - Status atual
    - Valor total
    - Dados do cliente (se associado)
    - Mesa (se associada)
    """,
    responses={
        200: {"description": "Pedido encontrado"},
        404: {"description": "Pedido não encontrado"}
    }
)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Busca um pedido de balcão por ID"""
    return svc.get_pedido(pedido_id)


from fastapi import APIRouter, Depends, Query
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
    "",
    response_model=list[PedidoBalcaoOut],
    summary="Listar pedidos abertos",
    description="""
    Lista todos os pedidos de balcão que estão abertos (não finalizados).
    
    **Status considerados abertos:**
    - PENDENTE
    - EM IMPRESSÃO
    - EM PREPARO
    - EDITADO / EM EDIÇÃO / AGUARDANDO PAGAMENTO
    
    **Ordenação:** Pedidos mais recentes primeiro.
    """,
    responses={
        200: {"description": "Lista de pedidos abertos"}
    }
)
def list_pedidos_abertos(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Lista todos os pedidos de balcão abertos"""
    return svc.list_pedidos_abertos(empresa_id=empresa_id)


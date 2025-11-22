from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

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
    "/finalizados",
    response_model=list[PedidoBalcaoOut],
    summary="Listar pedidos finalizados",
    description="""
    Lista todos os pedidos de balcão que foram finalizados (status ENTREGUE).
    
    **Filtros disponíveis:**
    - `data`: Filtra por data específica (YYYY-MM-DD). Se não informado, retorna todos os pedidos finalizados.
    
    **Ordenação:** Pedidos mais recentes primeiro.
    """,
    responses={
        200: {"description": "Lista de pedidos finalizados"}
    }
)
def list_pedidos_finalizados(
    data: date | None = Query(
        None,
        description="Filtrar por data (YYYY-MM-DD). Se não informado, retorna todos os pedidos finalizados"
    ),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Retorna todos os pedidos finalizados (ENTREGUE), opcionalmente filtrados por data"""
    return svc.list_pedidos_finalizados(data, empresa_id=empresa_id)


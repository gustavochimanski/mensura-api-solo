from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao_historico import HistoricoPedidoBalcaoResponse
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service


router = APIRouter(
    prefix="/api/balcao/admin/pedidos",
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/{pedido_id:int}/historico",
    response_model=HistoricoPedidoBalcaoResponse,
    summary="Obter histórico do pedido",
    description="""
    Obtém o histórico completo de alterações de um pedido de balcão.
    
    **Retorna:**
    - Todas as operações realizadas no pedido
    - Alterações de status
    - Adição/remoção de itens
    - Informações de quem executou cada operação
    - Timestamps de cada operação
    
    **Ordenação:** Operações mais recentes primeiro.
    """,
    responses={
        200: {"description": "Histórico retornado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def obter_historico_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros de histórico"),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Obtém o histórico completo de um pedido de balcão"""
    return svc.get_historico(pedido_id, limit=limit)


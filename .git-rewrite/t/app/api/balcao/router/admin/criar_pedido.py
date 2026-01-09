from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoCreate,
    PedidoBalcaoOut,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service


router = APIRouter(
    prefix="/api/balcao/admin/pedidos",
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/",
    response_model=PedidoBalcaoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar pedido de balcão",
    description="""
    Cria um novo pedido de balcão. 
    
    **Características:**
    - `mesa_id` é opcional (pode criar pedido sem mesa)
    - Pode ou não ter `cliente_id` associado
    - Permite adicionar itens durante a criação
    
    **Status inicial:** PENDENTE
    """,
    responses={
        201: {"description": "Pedido criado com sucesso"},
        400: {"description": "Dados inválidos ou produto não encontrado"},
        404: {"description": "Mesa não encontrada (se mesa_id informado)"}
    }
)
def criar_pedido(body: PedidoBalcaoCreate, db: Session = Depends(get_db), svc: PedidoBalcaoService = Depends(get_pedido_balcao_service)):
    """Cria um novo pedido de balcão"""
    return svc.criar_pedido(body)


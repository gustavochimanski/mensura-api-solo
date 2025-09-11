from datetime import date

from fastapi import APIRouter, status, Path, Query, Depends, Body
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido import FinalizarPedidoRequest, PedidoResponse, PedidoKanbanResponse, \
    EditarPedidoRequest
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum, PedidoStatusEnum
from app.api.delivery.services.service_pedido import PedidoService
from app.api.mensura.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos", tags=["Pedidos"])


# ======================================================================
# ============================ ADMIN ===================================
# ======================================================================
@router.get(
    "/admin/kanban",
    response_model=list[PedidoKanbanResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def listar_pedidos_admin_kanban(
    db: Session = Depends(get_db),
    date_filter: date | None = Query(None, description="Filtrar pedidos por data (YYYY-MM-DD)"),
    empresa_id: int = Query()
):
    """
    Lista pedidos do sistema (para admin, versão resumida pro Kanban)
    """
    return PedidoService(db).list_all_kanban(date_filter=date_filter, empresa_id=empresa_id)


@router.put(
    "/status/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido"),
    status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
):
    """
    Atualiza o status de um pedido (somente admin).
    """
    logger.info(f"[Pedidos] Atualizar status - pedido_id={pedido_id} -> {status}")
    svc = PedidoService(db)
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=status)


# ====================== ATUALIZAR PEDIDO ======================
@router.put(
    "/{pedido_id}/editar",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK
)
def atualizar_pedido(
        pedido_id: int = Path(..., description="ID do pedido a ser atualizado"),
        payload: EditarPedidoRequest = Body(...),
        db: Session = Depends(get_db),
        cliente=Depends(get_cliente_by_super_token)  # garante que o cliente só edita seus pedidos
):
    """
    Atualiza dados de um pedido existente:
    - meio_pagamento_id
    - endereco_id
    - cupom_id
    - observacao_geral
    - troco_para
    - itens
    """
    svc = PedidoService(db)

    # Verifica se o pedido pertence ao cliente
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido or pedido.cliente_telefone != cliente.telefone:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Pedido não encontrado para este cliente")

    # Atualiza o pedido via serviço
    return svc.editar_pedido(pedido_id, payload)


# ======================================================================
# ============================ CLIENTE =================================
# ======================================================================

@router.post("/checkout", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def checkout(
        payload: FinalizarPedidoRequest,
        db: Session = Depends(get_db),
        cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
):
    logger.info(f"[Pedidos] Checkout iniciado")
    svc = PedidoService(db)
    return svc.finalizar_pedido(payload, cliente.telefone)

@router.post("/{pedido_id}/confirmar-pagamento", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def confirmar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
    gateway: PagamentoGatewayEnum = PagamentoGatewayEnum.PIX_INTERNO,
    db: Session = Depends(get_db),
):
    logger.info(f"[Pedidos] Confirmar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}")
    svc = PedidoService(db)
    return await svc.confirmar_pagamento(pedido_id=pedido_id, metodo=metodo, gateway=gateway)

@router.get("/", response_model=list[PedidoResponse], status_code=status.HTTP_200_OK)
def listar_pedidos(
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    svc = PedidoService(db)
    return svc.listar_pedidos(cliente_telefone=cliente.telefone, skip=skip, limit=limit)

@router.get("/{pedido_id}", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
def get_pedido(pedido_id: int = Path(..., description="ID do pedido"), db: Session = Depends(get_db)):
    svc = PedidoService(db)
    return svc.get_pedido_by_id(pedido_id)






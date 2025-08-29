from fastapi import APIRouter, status, Path, Query, Depends
from sqlalchemy.orm import Session

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido_dv import FinalizarPedidoRequest, PedidoResponse
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum
from app.api.delivery.services.service_pedido import PedidoService
from app.api.mensura.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos", tags=["Pedidos"])

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

@router.put("/{pedido_id}", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
def editar_pedido(pedido_id: int, payload: FinalizarPedidoRequest, db: Session = Depends(get_db)):
    svc = PedidoService(db)
    return svc.editar_pedido(pedido_id=pedido_id, payload=payload)



# ======================================================================
# ============================ ADMIN ===================================
# ======================================================================
@router.get("/", response_model=list[PedidoResponse], status_code=status.HTTP_200_OK)
def listar_pedidos_admin(
    user: UserModel = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, description="Filtra por status do pedido"),
    db: Session = Depends(get_db),
):
    """
    Lista pedidos do sistema (para admin) com paginação e filtro opcional por status.
    """
    svc = PedidoService(db)
    return svc.listar_pedidos_admin(skip=skip, limit=limit, status=status_filter)
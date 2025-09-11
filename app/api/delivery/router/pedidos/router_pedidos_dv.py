from datetime import date
from typing import List

from fastapi import APIRouter, status, Path, Query, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido import FinalizarPedidoRequest, PedidoResponse, PedidoKanbanResponse, \
    EditarPedidoRequest, ItemPedidoEditar
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum, PedidoStatusEnum
from app.api.delivery.services.service_pedido import PedidoService
from app.core.admin_dependencies import get_current_user
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos", tags=["Pedidos"])

# ======================================================================
# =========================== CHECKOUT =================================
@router.post("/checkout", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def checkout(
        payload: FinalizarPedidoRequest,
        db: Session = Depends(get_db),
        cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
):
    logger.info(f"[Pedidos] Checkout iniciado")
    svc = PedidoService(db)
    return svc.finalizar_pedido(payload, cliente.telefone)

# ======================================================================
# ==================== CONFIRMAR PAGAMENTO =============================
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

# ======================================================================
# ====================== LISTAR PEDIDOS  ===============================
@router.get("/", response_model=list[PedidoResponse], status_code=status.HTTP_200_OK)
def listar_pedidos(
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    svc = PedidoService(db)
    return svc.listar_pedidos(cliente_telefone=cliente.telefone, skip=skip, limit=limit)

# ======================================================================
# ===================== GET PEDIDO BY ID ===============================
@router.get("/{pedido_id}", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
def get_pedido(pedido_id: int = Path(..., description="ID do pedido"), db: Session = Depends(get_db)):
    svc = PedidoService(db)
    return svc.get_pedido_by_id(pedido_id)

# ======================================================================
# ===================  ATUALIZA ITENS PEDIDO ===========================
@router.put(
    "/cliente/{pedido_id}/itens",
    response_model=PedidoResponse
)
def atualizar_itens_cliente(
    pedido_id: int = Path(..., description="ID do pedido"),
    itens: List[ItemPedidoEditar] = Body(...),
    cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db),
):
    """
    Atualiza os itens de um pedido do cliente: adicionar, atualizar ou remover.
    """
    svc = PedidoService(db)
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    if pedido.cliente_telefone != cliente.telefone:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    return svc.atualizar_itens_pedido(pedido_id, itens)

# ======================================================================
# =============== EDITA INFORMAÇÕES GERAIS PEDIDO ======================
@router.put(
    "/cliente/{pedido_id}/editar",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK
)
def atualizar_pedido_cliente(
        pedido_id: int = Path(..., description="ID do pedido a ser atualizado"),
        payload: EditarPedidoRequest = Body(...),
        cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
        db: Session = Depends(get_db),
):
    """
    Atualiza dados de um pedido existente, mas somente se for do próprio cliente.
    """
    svc = PedidoService(db)
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    if pedido.cliente_telefone != cliente.telefone:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    return svc.editar_pedido_parcial(pedido_id, payload)



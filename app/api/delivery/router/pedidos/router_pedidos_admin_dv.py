from datetime import date
from typing import List

from app.api.mensura.models.user_model import UserModel
from fastapi import APIRouter, status, Path, Query, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.schemas.schema_pedido import PedidoResponse, PedidoKanbanResponse, \
    EditarPedidoRequest, ItemPedidoEditar, PedidoResponseCompletoTotal, VincularEntregadorRequest
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.delivery.services.pedidos.service_pedido import PedidoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos/admin", tags=["Pedidos - Admin"])

# ======================================================================
# ===================== GET PEDIDO BY ID ===============================
@router.get("/{pedido_id}", response_model=PedidoResponseCompletoTotal, status_code=status.HTTP_200_OK)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido"), 
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    svc = PedidoService(db)
    return svc.get_pedido_by_id_completo_total(pedido_id)

# ======================================================================
# ============================ KANBAN ==================================
@router.get(
    "/kanban",
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


# ======================================================================
# ==================== ATUALIZA STATUS PEDIDO  ========================
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


# ======================================================================
# ================= ATUALIZAR INFO GERAL PEDIDO ========================
@router.put(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_pedido(
        pedido_id: int = Path(..., description="ID do pedido a ser atualizado"),
        payload: EditarPedidoRequest = Body(...),
        db: Session = Depends(get_db),
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

    # Atualiza o pedido via serviço
    return svc.editar_pedido_parcial(pedido_id, payload)


# ======================================================================
# ==================== ATUALIZAR ITENS PEDIDO ==========================
@router.put("/{pedido_id}/itens", response_model=PedidoResponse)
def atualizar_itens(
    pedido_id: int = Path(..., description="ID do pedido"),
    itens: List[ItemPedidoEditar] = ...,
    db: Session = Depends(get_db),
):
    """
    Atualiza os itens de um pedido: adicionar, atualizar quantidade/observação ou remover.
    """
    svc = PedidoService(db)
    # Verifica se o pedido pertence ao cliente
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    return svc.atualizar_itens_pedido(pedido_id, itens)


# ======================================================================
# ================= VINCULAR/DESVINCULAR ENTREGADOR ====================
@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def vincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido"),
    payload: VincularEntregadorRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Vincula ou desvincula um entregador a um pedido.
    - Para vincular: envie entregador_id com o ID do entregador
    - Para desvincular: envie entregador_id como null
    """
    logger.info(f"[Pedidos] Vincular entregador - pedido_id={pedido_id} -> entregador_id={payload.entregador_id}")
    svc = PedidoService(db)
    return svc.vincular_entregador(pedido_id, payload.entregador_id)


from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session

from app.api.delivery.schemas.schema_pedido import (
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoTotal,
    EditarPedidoRequest,
    ItemPedidoEditar,
    PedidoKanbanResponse,
)
from app.api.delivery.services.pedidos.service_pedido import PedidoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos/admin", tags=["Pedidos - Admin - Delivery"])

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
    empresa_id: int = Query(..., description="ID da empresa para filtrar pedidos", gt=0),
    limit: int = Query(500, ge=1, le=1000),
):
    """
    Lista pedidos do sistema para visualização no Kanban (admin).
    
    - **date_filter**: Filtra pedidos por data específica (formato YYYY-MM-DD)
    - **empresa_id**: ID da empresa (obrigatório, deve ser maior que 0)
    
    Retorna lista de pedidos com informações resumidas para o Kanban.
    """
    logger.info(f"[Pedidos] Listar Kanban - empresa_id={empresa_id}, date_filter={date_filter}")
    pedidos = PedidoService(db).list_all_kanban(
        date_filter=date_filter,
        empresa_id=empresa_id,
        limit=limit,
    )
    return pedidos

# ======================================================================
# ===================== GET PEDIDO BY ID ===============================
@router.get(
    "/{pedido_id}", 
    response_model=PedidoResponseCompletoTotal, 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0), 
    db: Session = Depends(get_db)
):
    """
    Busca um pedido específico com informações completas (admin).
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Retorna todos os dados do pedido incluindo itens, cliente, endereço, etc.
    """
    logger.info(f"[Pedidos] Buscar pedido - pedido_id={pedido_id}")
    svc = PedidoService(db)
    
    pedido = svc.get_pedido_by_id_completo_total(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return pedido


# ======================================================================
# ==================== ATUALIZA STATUS PEDIDO  ========================
@router.put(
    "/status/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    novo_status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
):
    """
    Atualiza o status de um pedido (somente admin).
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **novo_status**: Novo status do pedido (obrigatório)
    
    Status disponíveis: PENDENTE, CONFIRMADO, PREPARANDO, PRONTO, SAIU_PARA_ENTREGA, ENTREGUE, CANCELADO
    """
    logger.info(f"[Pedidos] Atualizar status - pedido_id={pedido_id} -> {novo_status}")
    svc = PedidoService(db)
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=novo_status)


# ======================================================================
# ================= ATUALIZAR INFO GERAL PEDIDO ========================
@router.put(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser atualizado", gt=0),
    payload: EditarPedidoRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Atualiza dados de um pedido existente (admin).
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **payload**: Dados para atualização
    
    Campos que podem ser atualizados:
    - **meio_pagamento_id**: ID do meio de pagamento
    - **endereco_id**: ID do endereço de entrega
    - **cupom_id**: ID do cupom de desconto
    - **observacao_geral**: Observação geral do pedido
    - **troco_para**: Valor do troco para
    - **itens**: Lista de itens do pedido
    """
    logger.info(f"[Pedidos] Atualizar pedido - pedido_id={pedido_id}")
    svc = PedidoService(db)
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )

    return svc.editar_pedido_parcial(pedido_id, payload)


# ======================================================================
# ==================== ATUALIZAR ITENS PEDIDO ==========================
@router.put(
    "/{pedido_id}/itens",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item: ItemPedidoEditar = Body(..., description="Ação a ser executada no item"),
    db: Session = Depends(get_db),
):
    """
    Executa uma única ação sobre os itens do pedido (adicionar, atualizar ou remover).
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **item**: Objeto descrevendo a ação a ser executada
    """
    logger.info(f"[Pedidos] Atualizar item - pedido_id={pedido_id}, acao={item.acao}")
    svc = PedidoService(db)

    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )

    return svc.atualizar_item_pedido(pedido_id, item)


# ======================================================================
# ================= VINCULAR/DESVINCULAR ENTREGADOR ====================
@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def vincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    entregador_id: int | None = Query(None, description="ID do entregador (omita para desvincular)", gt=0),
    db: Session = Depends(get_db),
):
    """
    Vincula ou desvincula um entregador a um pedido.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **entregador_id**: ID do entregador para vincular ou null para desvincular
    
    Para vincular: envie entregador_id com o ID do entregador
    Para desvincular: envie entregador_id como null
    """
    logger.info(f"[Pedidos] Vincular entregador - pedido_id={pedido_id} -> entregador_id={entregador_id}")
    svc = PedidoService(db)
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.vincular_entregador(pedido_id, entregador_id)


# ======================================================================
# ================= DESVINCULAR ENTREGADOR ============================
@router.delete(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def desvincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
):
    """
    Desvincula o entregador atual de um pedido.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Remove a vinculação do entregador com o pedido.
    """
    logger.info(f"[Pedidos] Desvincular entregador - pedido_id={pedido_id}")
    svc = PedidoService(db)
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.desvincular_entregador(pedido_id)

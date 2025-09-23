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
    empresa_id: int = Query(..., description="ID da empresa para filtrar pedidos", gt=0)
):
    """
    Lista pedidos do sistema para visualização no Kanban (admin).
    
    - **date_filter**: Filtra pedidos por data específica (formato YYYY-MM-DD)
    - **empresa_id**: ID da empresa (obrigatório, deve ser maior que 0)
    
    Retorna lista de pedidos com informações resumidas para o Kanban.
    """
    logger.info(f"[Pedidos] Listar Kanban - empresa_id={empresa_id}, date_filter={date_filter}")
    return PedidoService(db).list_all_kanban(date_filter=date_filter, empresa_id=empresa_id)

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
def atualizar_itens(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    itens: List[ItemPedidoEditar] = Body(..., description="Lista de itens para atualizar"),
    db: Session = Depends(get_db),
):
    """
    Atualiza os itens de um pedido: adicionar, atualizar quantidade/observação ou remover.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **itens**: Lista de itens para atualizar (obrigatório)
    
    Para cada item:
    - **item_id**: ID do item (para atualizar/remover) ou null (para adicionar)
    - **produto_id**: ID do produto (obrigatório para novos itens)
    - **quantidade**: Quantidade do item (obrigatório)
    - **observacao**: Observação específica do item (opcional)
    - **remover**: true para remover o item (opcional)
    """
    logger.info(f"[Pedidos] Atualizar itens - pedido_id={pedido_id}, itens_count={len(itens)}")
    svc = PedidoService(db)
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )

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
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: VincularEntregadorRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Vincula ou desvincula um entregador a um pedido.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **entregador_id**: ID do entregador para vincular ou null para desvincular
    
    Para vincular: envie entregador_id com o ID do entregador
    Para desvincular: envie entregador_id como null
    """
    logger.info(f"[Pedidos] Vincular entregador - pedido_id={pedido_id} -> entregador_id={payload.entregador_id}")
    svc = PedidoService(db)
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.vincular_entregador(pedido_id, payload.entregador_id)


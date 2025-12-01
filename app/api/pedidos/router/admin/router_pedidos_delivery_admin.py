from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session

from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.dependencies import get_pedido_service
from app.api.pedidos.schemas.schema_pedido import (
    FinalizarPedidoRequest,
    PedidoResponse,
    PedidoResponseCompletoTotal,
    EditarPedidoRequest,
    ItemPedidoEditar,
)
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.cadastros.models.user_model import UserModel
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/pedidos/admin/delivery",
    tags=["Admin - Pedidos Delivery"],
    dependencies=[Depends(get_current_user)],
)


# ======================================================================
# ============================ CREATE ==================================
# ======================================================================
@router.post(
    "/",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_pedido_delivery(
    payload: FinalizarPedidoRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Cria um novo pedido de delivery.
    
    **Campos obrigatórios:**
    - **empresa_id**: ID da empresa
    - **endereco_id**: ID do endereço de entrega
    - **meios_pagamento**: Lista de meios de pagamento
    - **produtos**: Objeto com itens, receitas e combos
    
    **Campos opcionais:**
    - **observacao_geral**: Observações gerais do pedido
    - **cupom_id**: ID do cupom de desconto
    - **troco_para**: Valor do troco (para pagamento em dinheiro)
    - **tipo_entrega**: Tipo de entrega (padrão: DELIVERY)
    - **origem**: Origem do pedido (padrão: WEB)
    """
    logger.info(f"[Pedidos Delivery] Criar pedido - empresa_id={payload.empresa_id}")
    
    # Para criar via admin, precisamos de um cliente_id
    # Se não fornecido no payload, pode ser necessário criar um cliente genérico
    # ou exigir que seja fornecido
    if not hasattr(payload, 'cliente_id') or payload.cliente_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "cliente_id é obrigatório para criar pedido de delivery via admin"
        )
    
    # Converte cliente_id para int se for string
    cliente_id = int(payload.cliente_id) if isinstance(payload.cliente_id, str) else payload.cliente_id
    
    return await svc.finalizar_pedido(payload, cliente_id=cliente_id)


# ======================================================================
# ============================ READ ====================================
# ======================================================================
@router.get(
    "/",
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_delivery(
    empresa_id: Optional[int] = Query(None, description="ID da empresa para filtrar", gt=0),
    cliente_id: Optional[int] = Query(None, description="ID do cliente para filtrar", gt=0),
    status_filter: Optional[PedidoStatusEnum] = Query(None, description="Filtrar por status"),
    data_inicio: Optional[date] = Query(None, description="Data de início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data de fim (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Lista pedidos de delivery com filtros opcionais.
    
    **Filtros disponíveis:**
    - **empresa_id**: Filtrar por empresa
    - **cliente_id**: Filtrar por cliente
    - **status_filter**: Filtrar por status do pedido
    - **data_inicio**: Filtrar pedidos a partir desta data
    - **data_fim**: Filtrar pedidos até esta data
    - **skip**: Número de registros para pular (padrão: 0)
    - **limit**: Limite de registros (padrão: 50, máximo: 200)
    """
    logger.info(
        f"[Pedidos Delivery] Listar - empresa_id={empresa_id}, cliente_id={cliente_id}, "
        f"status={status_filter}, data_inicio={data_inicio}, data_fim={data_fim}"
    )
    
    # Busca pedidos usando o repositório
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega, PedidoUnificadoModel
    from sqlalchemy import and_, or_
    from datetime import datetime, timedelta
    
    query = db.query(PedidoUnificadoModel).filter(
        PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value
    )
    
    if empresa_id:
        query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
    
    if cliente_id:
        query = query.filter(PedidoUnificadoModel.cliente_id == cliente_id)
    
    if status_filter:
        query = query.filter(PedidoUnificadoModel.status == status_filter.value)
    
    if data_inicio:
        start_dt = datetime.combine(data_inicio, datetime.min.time())
        query = query.filter(PedidoUnificadoModel.created_at >= start_dt)
    
    if data_fim:
        end_dt = datetime.combine(data_fim, datetime.max.time())
        query = query.filter(PedidoUnificadoModel.created_at <= end_dt)
    
    pedidos = query.order_by(PedidoUnificadoModel.created_at.desc()).offset(skip).limit(limit).all()
    
    # Converte para PedidoResponse usando o response builder
    return [svc.response_builder.build_pedido_response(p) for p in pedidos]


@router.get(
    "/{pedido_id}",
    response_model=PedidoResponseCompletoTotal,
    status_code=status.HTTP_200_OK,
)
def obter_pedido_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Obtém um pedido de delivery específico por ID com todas as informações.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    """
    logger.info(f"[Pedidos Delivery] Obter pedido - pedido_id={pedido_id}")
    
    pedido = svc.get_pedido_by_id_completo_total(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido de delivery com ID {pedido_id} não encontrado"
        )
    
    # Verifica se é um pedido de delivery
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    pedido_model = svc.repo.get_pedido(pedido_id)
    if pedido_model and pedido_model.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return pedido


@router.get(
    "/cliente/{cliente_id}",
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_por_cliente(
    cliente_id: int = Path(..., description="ID do cliente", gt=0),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Lista pedidos de delivery de um cliente específico.
    
    - **cliente_id**: ID do cliente (obrigatório)
    - **skip**: Número de registros para pular (padrão: 0)
    - **limit**: Limite de registros (padrão: 50, máximo: 200)
    """
    logger.info(f"[Pedidos Delivery] Listar por cliente - cliente_id={cliente_id}")
    return svc.listar_pedidos(cliente_id=cliente_id, skip=skip, limit=limit)


# ======================================================================
# ============================ UPDATE ==================================
# ======================================================================
@router.put(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_pedido_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: EditarPedidoRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Atualiza informações gerais de um pedido de delivery.
    
    **Campos atualizáveis:**
    - **meio_pagamento_id**: ID do meio de pagamento
    - **endereco_id**: ID do endereço de entrega
    - **cupom_id**: ID do cupom de desconto
    - **observacao_geral**: Observações gerais
    - **troco_para**: Valor do troco
    
    - **pedido_id**: ID do pedido (obrigatório)
    """
    logger.info(f"[Pedidos Delivery] Atualizar pedido - pedido_id={pedido_id}")
    
    # Verifica se é um pedido de delivery
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.editar_pedido_parcial(pedido_id, payload)


@router.put(
    "/{pedido_id}/itens",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_itens_pedido_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item: ItemPedidoEditar = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Atualiza itens de um pedido de delivery.
    
    **Ações disponíveis:**
    - **adicionar**: Adiciona um novo item ao pedido
    - **atualizar**: Atualiza um item existente (quantidade, observação)
    - **remover**: Remove um item do pedido
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **item**: Objeto com a ação e dados do item
    """
    logger.info(f"[Pedidos Delivery] Atualizar itens - pedido_id={pedido_id}")
    
    # Verifica se é um pedido de delivery
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.atualizar_item_pedido(pedido_id, item)


@router.put(
    "/{pedido_id}/status",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_status_pedido_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    novo_status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Atualiza o status de um pedido de delivery.
    
    **Status disponíveis:**
    - **P**: PENDENTE
    - **I**: EM IMPRESSÃO
    - **R**: EM PREPARO
    - **S**: SAIU PARA ENTREGA
    - **E**: ENTREGUE
    - **C**: CANCELADO
    - **D**: EDITADO
    - **X**: EM EDIÇÃO
    - **A**: AGUARDANDO PAGAMENTO
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **novo_status**: Novo status do pedido (obrigatório)
    """
    logger.info(f"[Pedidos Delivery] Atualizar status - pedido_id={pedido_id} -> {novo_status} (user={current_user.id})")
    
    # Verifica se é um pedido de delivery
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=novo_status, user_id=current_user.id)


@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def vincular_entregador_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    entregador_id: Optional[int] = Query(None, description="ID do entregador (omita ou envie null para desvincular)"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Vincula ou desvincula um entregador a um pedido de delivery.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **entregador_id**: ID do entregador para vincular ou null/omitido para desvincular
    
    **Validações:**
    - Pedido deve existir e ser de delivery
    - Entregador deve existir (se fornecido)
    - Entregador deve estar vinculado à empresa do pedido
    """
    logger.info(f"[Pedidos Delivery] Vincular entregador - pedido_id={pedido_id} -> entregador_id={entregador_id}")
    
    # Verifica se é um pedido de delivery
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.vincular_entregador(pedido_id, entregador_id)


# ======================================================================
# ============================ DELETE ==================================
# ======================================================================
@router.delete(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def cancelar_pedido_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Cancela um pedido de delivery.
    
    - **pedido_id**: ID do pedido (obrigatório)
    
    **Nota:** Este endpoint cancela o pedido (status CANCELADO).
    """
    logger.info(f"[Pedidos Delivery] Cancelar pedido - pedido_id={pedido_id} (user={current_user.id})")
    
    # Verifica se é um pedido de delivery
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=PedidoStatusEnum.C, user_id=current_user.id)


@router.delete(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def desvincular_entregador_delivery(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Desvincula o entregador atual de um pedido de delivery.
    
    - **pedido_id**: ID do pedido (obrigatório)
    
    Remove a vinculação do entregador com o pedido.
    """
    logger.info(f"[Pedidos Delivery] Desvincular entregador - pedido_id={pedido_id}")
    
    # Verifica se é um pedido de delivery
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.desvincular_entregador(pedido_id)


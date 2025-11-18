"""
Router admin para pedidos unificados.
"""
from fastapi import APIRouter, Depends, Path, status, Query, Body
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, List

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.pedidos.services.dependencies import get_pedido_service
from app.api.pedidos.services.service_pedidos import PedidoService
from app.api.pedidos.schemas.schema_pedido import (
    PedidoCreate,
    PedidoOut,
    PedidoUpdate,
    PedidoItemIn,
    StatusPedidoEnum,
    TipoPedidoEnum,
)
from app.api.cadastros.models.user_model import UserModel


router = APIRouter(
    prefix="/api/pedidos/admin",
    tags=["Admin - Pedidos Unificados"],
    dependencies=[Depends(get_current_user)],
)


# -------- CRUD --------
@router.post(
    "",
    response_model=PedidoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar pedido",
    description="""
    Cria um novo pedido. Suporta três tipos:
    - **MESA**: Pedidos de mesa (mesa_id obrigatório)
    - **BALCAO**: Pedidos de balcão (mesa_id opcional)
    - **DELIVERY**: Pedidos de delivery (endereco_id obrigatório)
    
    **Validações específicas por tipo:**
    - MESA: mesa_id obrigatório
    - DELIVERY: endereco_id obrigatório
    """,
    responses={
        201: {"description": "Pedido criado com sucesso"},
        400: {"description": "Dados inválidos"},
        404: {"description": "Mesa/Endereço não encontrado"}
    }
)
def criar_pedido(
    body: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
) -> PedidoOut:
    """Cria um novo pedido"""
    return svc.criar_pedido(body, usuario_id=current_user.id)


@router.get(
    "/{pedido_id:int}",
    response_model=PedidoOut,
    summary="Buscar pedido por ID",
    description="Busca um pedido específico pelo ID.",
    responses={
        200: {"description": "Pedido encontrado"},
        404: {"description": "Pedido não encontrado"}
    }
)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Busca um pedido por ID"""
    return svc.get_pedido(pedido_id)


@router.patch(
    "/{pedido_id:int}",
    response_model=PedidoOut,
    summary="Atualizar pedido",
    description="Atualiza um pedido existente.",
    responses={
        200: {"description": "Pedido atualizado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def atualizar_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: PedidoUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Atualiza um pedido"""
    return svc.atualizar_pedido(pedido_id, body, usuario_id=current_user.id)


# -------- Itens --------
@router.post(
    "/{pedido_id:int}/itens",
    response_model=PedidoOut,
    summary="Adicionar item ao pedido",
    description="Adiciona um novo item ao pedido.",
    responses={
        200: {"description": "Item adicionado com sucesso"},
        400: {"description": "Pedido fechado/cancelado ou dados inválidos"},
        404: {"description": "Pedido não encontrado"}
    }
)
def adicionar_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: PedidoItemIn = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Adiciona um item ao pedido"""
    return svc.adicionar_item(pedido_id, body, usuario_id=current_user.id)


@router.delete(
    "/{pedido_id:int}/itens/{item_id:int}",
    response_model=PedidoOut,
    summary="Remover item do pedido",
    description="Remove um item específico do pedido.",
    responses={
        200: {"description": "Item removido com sucesso"},
        400: {"description": "Pedido fechado/cancelado"},
        404: {"description": "Pedido ou item não encontrado"}
    }
)
def remover_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item_id: int = Path(..., description="ID do item", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Remove um item do pedido"""
    return svc.remover_item(pedido_id, item_id, usuario_id=current_user.id)


# -------- Fluxo Pedido --------
@router.post(
    "/{pedido_id:int}/cancelar",
    response_model=PedidoOut,
    summary="Cancelar pedido",
    description="Cancela um pedido, alterando seu status para CANCELADO.",
    responses={
        200: {"description": "Pedido cancelado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def cancelar_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Cancela um pedido"""
    return svc.cancelar_pedido(pedido_id, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/finalizar",
    response_model=PedidoOut,
    summary="Finalizar pedido",
    description="Finaliza um pedido, alterando seu status para ENTREGUE.",
    responses={
        200: {"description": "Pedido finalizado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def finalizar_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Finaliza um pedido"""
    return svc.finalizar_pedido(pedido_id, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/status",
    response_model=PedidoOut,
    summary="Atualizar status do pedido",
    description="Atualiza manualmente o status de um pedido.",
    responses={
        200: {"description": "Status atualizado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    novo_status: StatusPedidoEnum = Body(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Atualiza o status de um pedido"""
    return svc.atualizar_status(pedido_id, novo_status, usuario_id=current_user.id)


# -------- Consultas --------
@router.get(
    "/abertos",
    response_model=List[PedidoOut],
    summary="Listar pedidos abertos",
    description="""
    Lista todos os pedidos que estão abertos (não finalizados).
    
    **Filtros:**
    - `tipo_pedido`: Filtrar por tipo (MESA, BALCAO, DELIVERY)
    """,
    responses={
        200: {"description": "Lista de pedidos abertos"}
    }
)
def list_pedidos_abertos(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    tipo_pedido: Optional[TipoPedidoEnum] = Query(None, description="Filtrar por tipo de pedido"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Lista todos os pedidos abertos"""
    tipo = tipo_pedido.value if tipo_pedido else None
    return svc.list_pedidos_abertos(empresa_id=empresa_id, tipo_pedido=tipo)


@router.get(
    "/finalizados",
    response_model=List[PedidoOut],
    summary="Listar pedidos finalizados",
    description="""
    Lista todos os pedidos que foram finalizados (status ENTREGUE).
    
    **Filtros:**
    - `data`: Filtrar por data específica (YYYY-MM-DD)
    - `tipo_pedido`: Filtrar por tipo (MESA, BALCAO, DELIVERY)
    """,
    responses={
        200: {"description": "Lista de pedidos finalizados"}
    }
)
def list_pedidos_finalizados(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    data: Optional[date] = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    tipo_pedido: Optional[TipoPedidoEnum] = Query(None, description="Filtrar por tipo de pedido"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Lista pedidos finalizados"""
    tipo = tipo_pedido.value if tipo_pedido else None
    return svc.list_pedidos_finalizados(data, empresa_id=empresa_id, tipo_pedido=tipo)


@router.get(
    "/cliente/{cliente_id:int}",
    response_model=List[PedidoOut],
    summary="Listar pedidos por cliente",
    description="Lista todos os pedidos de um cliente específico.",
    responses={
        200: {"description": "Lista de pedidos do cliente"}
    }
)
def list_pedidos_by_cliente(
    cliente_id: int = Path(..., description="ID do cliente", gt=0),
    empresa_id: Optional[int] = Query(None, gt=0, description="ID da empresa"),
    tipo_pedido: Optional[TipoPedidoEnum] = Query(None, description="Filtrar por tipo de pedido"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de registros"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Lista pedidos de um cliente"""
    tipo = tipo_pedido.value if tipo_pedido else None
    return svc.list_pedidos_by_cliente(
        cliente_id,
        empresa_id=empresa_id,
        tipo_pedido=tipo,
        skip=skip,
        limit=limit
    )


@router.get(
    "/tipo/{tipo_pedido:str}",
    response_model=List[PedidoOut],
    summary="Listar pedidos por tipo",
    description="Lista pedidos filtrados por tipo específico.",
    responses={
        200: {"description": "Lista de pedidos do tipo especificado"}
    }
)
def list_pedidos_by_tipo(
    tipo_pedido: TipoPedidoEnum = Path(..., description="Tipo do pedido"),
    empresa_id: Optional[int] = Query(None, gt=0, description="ID da empresa"),
    status: Optional[StatusPedidoEnum] = Query(None, description="Filtrar por status"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=100, description="Número máximo de registros"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Lista pedidos por tipo"""
    status_value = status.value if status else None
    return svc.list_pedidos_by_tipo(
        tipo_pedido.value,
        empresa_id=empresa_id,
        status=status_value,
        skip=skip,
        limit=limit
    )


@router.get(
    "/{pedido_id:int}/historico",
    summary="Obter histórico do pedido",
    description="Obtém o histórico completo de alterações de um pedido.",
    responses={
        200: {"description": "Histórico retornado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def obter_historico_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros de histórico"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """Obtém o histórico completo de um pedido"""
    return svc.get_historico(pedido_id, limit=limit)


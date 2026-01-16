from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.pedidos.schemas import (
    HistoricoDoPedidoResponse,
    KanbanAgrupadoResponse,
    PedidoCreateRequest,
    PedidoEntregadorRequest,
    PedidoFecharContaRequest,
    PedidoItemMutationAction,
    PedidoItemMutationRequest,
    PedidoObservacaoPatchRequest,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoTotal,
    PedidoStatusPatchRequest,
    PedidoUpdateRequest,
)
from app.api.pedidos.services.service_pedido_admin import PedidoAdminService
from app.api.pedidos.services.dependencies import get_pedido_admin_service
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum
from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user


router = APIRouter(
    prefix="/api/pedidos/admin",
    tags=["Admin - Pedidos Unificados"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "",
    response_model=list[PedidoResponse],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos(
    empresa_id: Optional[int] = Query(None, description="Filtra por empresa"),
    tipo: Optional[List[TipoEntregaEnum]] = Query(
        None,
        description="Filtra por tipo de pedido (DELIVERY, RETIRADA, BALCAO, MESA). Pode ser usado múltiplas vezes.",
    ),
    status_filter: Optional[List[PedidoStatusEnum]] = Query(
        None,
        description="Filtra por status do pedido. Pode ser usado múltiplas vezes.",
    ),
    cliente_id: Optional[int] = Query(None, description="Filtra por cliente"),
    mesa_id: Optional[int] = Query(None, description="Filtra por mesa"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Quantidade de registros a pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.listar_pedidos(
        empresa_id=empresa_id,
        tipos=tipo,
        status_list=status_filter,
        cliente_id=cliente_id,
        mesa_id=mesa_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/kanban",
    response_model=KanbanAgrupadoResponse,
    status_code=status.HTTP_200_OK,
)
def listar_kanban(
    date_filter: date = Query(..., description="Data alvo no formato YYYY-MM-DD"),
    empresa_id: int = Query(..., gt=0, description="Empresa para filtragem"),
    limit: int = Query(500, ge=1, le=1000, description="Limite de pedidos por agrupamento"),
    tipo: Optional[TipoEntregaEnum] = Query(
        None,
        description="Filtra por tipo de pedido (DELIVERY, BALCAO, MESA). Se informado, retorna apenas pedidos deste tipo.",
    ),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.listar_kanban(
        date_filter=date_filter,
        empresa_id=empresa_id,
        limit=limit,
        tipo=tipo,
    )


@router.get(
    "/{pedido_id}",
    response_model=PedidoResponseCompletoTotal,
    status_code=status.HTTP_200_OK,
)
def obter_pedido(
    pedido_id: int = Path(..., gt=0, description="Identificador do pedido"),
    empresa_id: Optional[int] = Query(None, description="ID da empresa para validação (opcional)"),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Obtém os detalhes completos de um pedido específico.

    Esta rota retorna todas as informações de um pedido, incluindo itens,
    histórico, status e demais dados relacionados. O parâmetro empresa_id
    é opcional e pode ser usado para validação adicional de permissões.

    Args:
        pedido_id: Identificador único do pedido (deve ser maior que 0).
        empresa_id: ID da empresa para validação de acesso (opcional).
        svc: Serviço de administração de pedidos (injetado via dependência).

    Returns:
        PedidoResponseCompletoTotal: Objeto contendo todos os dados do pedido,
            incluindo informações completas e totais.

    Raises:
        HTTPException: 404 se o pedido não for encontrado.
        HTTPException: 403 se o usuário não tiver permissão para acessar o pedido.
    """
    return svc.obter_pedido(pedido_id, empresa_id=empresa_id)


@router.get(
    "/{pedido_id}/historico",
    response_model=HistoricoDoPedidoResponse,
    status_code=status.HTTP_200_OK,
)
def obter_historico(
    pedido_id: int = Path(..., gt=0, description="Identificador do pedido"),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.obter_historico(pedido_id)


@router.post(
    "",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_201_CREATED,
)
async def criar_pedido(
    payload: PedidoCreateRequest = Body(...),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return await svc.criar_pedido(payload)


@router.put(
    "/{pedido_id}",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_pedido(
    pedido_id: int = Path(..., gt=0),
    payload: PedidoUpdateRequest = Body(...),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.atualizar_pedido(pedido_id, payload)


@router.patch(
    "/{pedido_id}/status",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_status(
    pedido_id: int = Path(..., gt=0),
    payload: PedidoStatusPatchRequest = Body(...),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.atualizar_status(
        pedido_id=pedido_id,
        payload=payload,
        user_id=current_user.id if current_user else None,
    )


@router.delete(
    "/{pedido_id}",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def cancelar_pedido(
    pedido_id: int = Path(..., gt=0),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.cancelar(
        pedido_id=pedido_id,
        user_id=current_user.id if current_user else None,
    )


@router.patch(
    "/{pedido_id}/observacoes",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_observacoes(
    pedido_id: int = Path(..., gt=0),
    payload: PedidoObservacaoPatchRequest = Body(...),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.atualizar_observacoes(pedido_id, payload)


@router.patch(
    "/{pedido_id}/fechar-conta",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def fechar_conta(
    pedido_id: int = Path(..., gt=0),
    payload: Optional[PedidoFecharContaRequest] = Body(None),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.fechar_conta(pedido_id, payload)


@router.patch(
    "/{pedido_id}/reabrir",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def reabrir_pedido(
    pedido_id: int = Path(..., gt=0),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.reabrir(pedido_id)


@router.post(
    "/{pedido_id}/itens",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def gerenciar_itens(
    pedido_id: int = Path(..., gt=0),
    payload: PedidoItemMutationRequest = Body(...),
    tipo: Optional[TipoEntregaEnum] = Query(
        None,
        description="Tipo de pedido (DELIVERY, BALCAO, MESA). Opcional - será detectado automaticamente pelo pedido_id se não informado.",
    ),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Endpoint unificado para gerenciar itens de pedidos (Delivery, Balcão e Mesa).
    
    Suporta adicionar, atualizar e remover produtos, receitas e combos.
    Todos os tipos de pedido suportam complementos.
    
    O parâmetro `tipo` é opcional e serve apenas para validação.
    O tipo real do pedido é detectado automaticamente pelo `pedido_id`.
    """
    # Se tipo foi informado na query, adiciona ao payload para validação
    if tipo:
        payload.tipo = tipo
    return svc.gerenciar_item(pedido_id, payload)


@router.patch(
    "/{pedido_id}/itens/{item_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_item(
    pedido_id: int = Path(..., gt=0),
    item_id: int = Path(..., gt=0),
    payload: PedidoItemMutationRequest = Body(...),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    mutation = PedidoItemMutationRequest(
        **payload.model_dump(exclude={'acao', 'item_id'}),
        acao=PedidoItemMutationAction.UPDATE,
        item_id=item_id,
    )
    return svc.gerenciar_item(pedido_id, mutation)


@router.delete(
    "/{pedido_id}/itens/{item_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def remover_item(
    pedido_id: int = Path(..., gt=0),
    item_id: int = Path(..., gt=0),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.remover_item(pedido_id, item_id)


@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_entregador(
    pedido_id: int = Path(..., gt=0),
    payload: PedidoEntregadorRequest = Body(...),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.atualizar_entregador(pedido_id, payload)


@router.delete(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def remover_entregador(
    pedido_id: int = Path(..., gt=0),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    return svc.remover_entregador(pedido_id)


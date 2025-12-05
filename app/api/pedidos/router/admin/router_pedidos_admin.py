"""
Router unificado de pedidos para admin.
Agora todos os tipos de pedidos (Delivery, Mesa, Balcão) usam a mesma tabela unificada.
Todos os endpoints estão centralizados aqui.
"""
from datetime import date
from typing import Optional, List
import os

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    Path,
    Body,
    Request,
    Response,
)

from app.api.pedidos.schemas.schema_pedido import (
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoTotal,
    EditarPedidoRequest,
    ItemPedidoEditar,
    KanbanAgrupadoResponse,
    FinalizarPedidoRequest,
    ProdutosPedidoRequest,
)
from app.api.pedidos.schemas import (
    PedidoStatusPatchRequest,
    PedidoCreateRequest,
    PedidoUpdateRequest,
    PedidoItemMutationRequest,
    PedidoItemMutationAction,
    PedidoEntregadorRequest,
    PedidoObservacaoPatchRequest,
    PedidoFecharContaRequest,
)
from app.api.pedidos.schemas.schema_pedido_status_historico import HistoricoDoPedidoResponse
from app.api.pedidos.services.service_pedido_admin import PedidoAdminService
from app.api.pedidos.services.dependencies import get_pedido_admin_service
from app.api.pedidos.services.service_pedidos_mesa import (
    PedidoMesaCreate,
    AdicionarItemRequest,
    AdicionarProdutoGenericoRequest,
    RemoverItemResponse,
    FecharContaMesaRequest,
    AtualizarObservacoesRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
from app.core.admin_dependencies import get_current_user
from app.api.cadastros.models.user_model import UserModel
from app.utils.logger import logger
from app.api.pedidos.schemas.schema_pedido import TipoPedidoCheckoutEnum

router = APIRouter(
    prefix="/api/pedidos/admin",
    tags=["Admin - Pedidos Unificados"],
    dependencies=[Depends(get_current_user)]
)

PEDIDOS_V2_ENABLED = os.getenv("PEDIDOS_V2_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def _emit_v2_warning(response: Response, request: Request, legacy_route: str, v2_route: str) -> None:
    """
    Adiciona headers de depreciação e, quando habilitado, redireciona consumidores para a rota v2 equivalente.
    """
    response.headers.setdefault("Deprecation", "true")
    response.headers.setdefault("Link", f'<{v2_route}>; rel="successor-version"')

    logger.warning(
        "[Pedidos][Compat] Rota legada %s utilizada. Sugerido migrar para %s. user_agent=%s empresa=%s",
        legacy_route,
        v2_route,
        request.headers.get("user-agent"),
        request.headers.get("x-empresa-id"),
    )

    if PEDIDOS_V2_ENABLED and request.headers.get("x-api-version", "").strip() == "2":
        raise HTTPException(
            status_code=status.HTTP_308_PERMANENT_REDIRECT,
            detail="Esta rota foi substituída pela versão v2.",
            headers={"Location": v2_route},
        )


# ======================================================================
# ============================ KANBAN ==================================
# ======================================================================
@router.get(
    "/kanban",
    response_model=KanbanAgrupadoResponse,
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_admin_kanban(
    request: Request,
    response: Response,
    date_filter: date = Query(..., description="Filtrar pedidos por data (YYYY-MM-DD) - OBRIGATÓRIO"),
    empresa_id: int = Query(..., description="ID da empresa para filtrar pedidos", gt=0),
    limit: int = Query(500, ge=1, le=1000),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Lista pedidos do sistema para visualização no Kanban (admin).
    
    **Retorno agrupado por categoria:**
    - `delivery`: Array de pedidos de delivery
    - `balcao`: Array de pedidos de balcão
    - `mesas`: Array de pedidos de mesas
    
    Cada categoria mantém seus IDs originais (sem conflitos).
    
    - **date_filter**: Filtra pedidos por data específica (formato YYYY-MM-DD) - OBRIGATÓRIO
    - **empresa_id**: ID da empresa (obrigatório, deve ser maior que 0)
    - **limit**: Limite de pedidos por categoria (padrão: 500)
    """
    _emit_v2_warning(response, request, request.url.path, "/api/pedidos/admin/v2/kanban")
    logger.info(f"[Pedidos] Listar Kanban - empresa_id={empresa_id}, date_filter={date_filter}")
    return svc.listar_kanban(
        date_filter=date_filter,
        empresa_id=empresa_id,
        limit=limit,
    )


# ======================================================================
# ====================== PEDIDOS GERAIS ===============================
# ======================================================================
@router.get(
    "/{pedido_id}",
    response_model=PedidoResponseCompletoTotal,
    status_code=status.HTTP_200_OK,
)
def get_pedido(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Busca um pedido específico com informações completas (admin).
    Funciona para todos os tipos: Delivery, Mesa e Balcão.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Retorna todos os dados do pedido incluindo itens, cliente, endereço, etc.
    """
    logger.info(f"[Pedidos] Buscar pedido - pedido_id={pedido_id}")
    
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}",
    )
    return svc.obter_pedido(pedido_id)


@router.get(
    "/{pedido_id}/historico",
    response_model=HistoricoDoPedidoResponse,
    status_code=status.HTTP_200_OK,
)
def obter_historico_pedido(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Obtém o histórico completo de alterações de status de um pedido.
    Funciona para todos os tipos: Delivery, Mesa e Balcão.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Retorna todos os registros de mudança de status com timestamps, motivos e observações.
    """
    logger.info(f"[Pedidos] Obter histórico - pedido_id={pedido_id}")
    
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/historico",
    )
    return svc.obter_historico(pedido_id)


@router.put(
    "/{pedido_id}/status",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_status_pedido(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    novo_status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Atualiza o status de um pedido (Delivery, Mesa ou Balcão).
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **novo_status**: Novo status do pedido (obrigatório)
    
    Status disponíveis: P, I, R, S, E, C, D, X, A
    - P = PENDENTE
    - I = EM IMPRESSÃO
    - R = EM PREPARO
    - S = SAIU PARA ENTREGA
    - E = ENTREGUE
    - C = CANCELADO
    - D = EDITADO
    - X = EM EDIÇÃO
    - A = AGUARDANDO PAGAMENTO
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/status?status={novo_status.value}",
    )

    logger.info(f"[Pedidos] Atualizar status - pedido_id={pedido_id} -> {novo_status} (user={current_user.id})")
    
    patch = PedidoStatusPatchRequest(status=novo_status)
    svc.atualizar_status(
        pedido_id=pedido_id,
        payload=patch,
        user_id=current_user.id if current_user else None,
    )

    pedido_atualizado = svc.repo.get_pedido(pedido_id)
    if not pedido_atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado após atualização",
        )

    return svc.pedido_service.response_builder.build_pedido_response(pedido_atualizado)


@router.delete(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def cancelar_pedido(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Cancela um pedido (Delivery, Mesa ou Balcão).
    
    - **pedido_id**: ID do pedido (obrigatório)
    
    **Nota:** Este endpoint cancela o pedido (status CANCELADO).
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}",
    )

    logger.info(f"[Pedidos] Cancelar pedido - pedido_id={pedido_id} (user={current_user.id})")
    
    svc.cancelar(
        pedido_id=pedido_id,
        user_id=current_user.id if current_user else None,
    )

    pedido_atualizado = svc.repo.get_pedido(pedido_id)
    if not pedido_atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado após cancelamento",
        )

    return svc.pedido_service.response_builder.build_pedido_response(pedido_atualizado)


# ======================================================================
# ====================== DELIVERY ======================================
# ======================================================================
@router.post(
    "/delivery",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_pedido_delivery(
    request: Request,
    response: Response,
    payload: FinalizarPedidoRequest = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
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
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        "/api/pedidos/admin/v2",
    )

    logger.info(f"[Pedidos Delivery] Criar pedido - empresa_id={payload.empresa_id}")
    
    create_payload = PedidoCreateRequest(**payload.model_dump())
    create_payload.tipo_pedido = TipoPedidoCheckoutEnum.DELIVERY

    pedido_criado = await svc_admin.criar_pedido(create_payload)
    pedido_model = svc_admin.repo.get_pedido(pedido_criado.id)
    if not pedido_model:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Falha ao recuperar pedido criado.",
        )
    return svc_admin._build_pedido_response(pedido_model)


@router.get(
    "/delivery",
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_delivery(
    request: Request,
    response: Response,
    empresa_id: Optional[int] = Query(None, description="ID da empresa para filtrar", gt=0),
    cliente_id: Optional[int] = Query(None, description="ID do cliente para filtrar", gt=0),
    status_filter: Optional[PedidoStatusEnum] = Query(None, description="Filtrar por status"),
    data_inicio: Optional[date] = Query(None, description="Data de início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data de fim (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
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
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        "/api/pedidos/admin/v2",
    )

    logger.info(
        f"[Pedidos Delivery] Listar - empresa_id={empresa_id}, cliente_id={cliente_id}, "
        f"status={status_filter}, data_inicio={data_inicio}, data_fim={data_fim}"
    )
    
    status_list = [status_filter] if status_filter else None

    return svc_admin.listar_pedidos(
        empresa_id=empresa_id,
        tipos=[TipoEntregaEnum.DELIVERY],
        status_list=status_list,
        cliente_id=cliente_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/delivery/cliente/{cliente_id}",
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_delivery_por_cliente(
    request: Request,
    response: Response,
    cliente_id: int = Path(..., description="ID do cliente", gt=0),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Lista pedidos de delivery de um cliente específico.
    
    - **cliente_id**: ID do cliente (obrigatório)
    - **skip**: Número de registros para pular (padrão: 0)
    - **limit**: Limite de registros (padrão: 50, máximo: 200)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2?cliente_id={cliente_id}",
    )

    logger.info(f"[Pedidos Delivery] Listar por cliente - cliente_id={cliente_id}")
    return svc_admin.listar_pedidos(
        cliente_id=cliente_id,
        tipos=[TipoEntregaEnum.DELIVERY],
        skip=skip,
        limit=limit,
    )


@router.put(
    "/delivery/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_pedido_delivery(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: EditarPedidoRequest = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
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
    
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}",
    )

    update_payload = PedidoUpdateRequest(**payload.model_dump())
    svc_admin.atualizar_pedido(pedido_id, update_payload)

    pedido_atualizado = svc_admin.repo.get_pedido(pedido_id)
    if not pedido_atualizado or pedido_atualizado.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado",
        )

    return svc_admin._build_pedido_response(pedido_atualizado)


@router.put(
    "/delivery/{pedido_id}/itens",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_itens_pedido_delivery(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item: ItemPedidoEditar = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
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
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/itens",
    )

    logger.info(f"[Pedidos Delivery] Atualizar itens - pedido_id={pedido_id}")
    
    acao_map = {
        "adicionar": PedidoItemMutationAction.ADD,
        "atualizar": PedidoItemMutationAction.UPDATE,
        "remover": PedidoItemMutationAction.REMOVE,
    }
    acao = acao_map.get(item.acao.lower()) if isinstance(item.acao, str) else None
    if acao is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ação inválida: {item.acao}",
        )

    mutation = PedidoItemMutationRequest(
        acao=acao,
        item_id=item.id,
        produto_cod_barras=item.produto_cod_barras,
        quantidade=item.quantidade,
        observacao=item.observacao,
    )
    return svc_admin.gerenciar_item(pedido_id, mutation)


@router.put(
    "/delivery/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def vincular_entregador_delivery(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    entregador_id: Optional[int] = Query(None, description="ID do entregador (omita ou envie null para desvincular)"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
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
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/entregador",
    )

    logger.info(f"[Pedidos Delivery] Vincular entregador - pedido_id={pedido_id} -> entregador_id={entregador_id}")
    
    request = PedidoEntregadorRequest(entregador_id=entregador_id)
    return svc_admin.atualizar_entregador(pedido_id, request)


@router.delete(
    "/delivery/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def desvincular_entregador_delivery(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Desvincula o entregador atual de um pedido de delivery.
    
    - **pedido_id**: ID do pedido (obrigatório)
    
    Remove a vinculação do entregador com o pedido.
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/entregador",
    )

    logger.info(f"[Pedidos Delivery] Desvincular entregador - pedido_id={pedido_id}")
    
    return svc_admin.remover_entregador(pedido_id)


# ======================================================================
# ====================== MESA =========================================
# ======================================================================
@router.post(
    "/mesa",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_201_CREATED,
)
async def criar_pedido_mesa(
    request: Request,
    response: Response,
    payload: PedidoMesaCreate = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Cria um novo pedido de mesa.
    
    - **empresa_id**: ID da empresa (obrigatório)
    - **mesa_id**: Código da mesa (obrigatório)
    - **cliente_id**: ID do cliente (opcional)
    - **observacoes**: Observações gerais do pedido (opcional)
    - **num_pessoas**: Número de pessoas na mesa (opcional)
    - **itens**: Lista de itens iniciais do pedido (opcional)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        "/api/pedidos/admin/v2",
    )

    logger.info(f"[Pedidos Mesa] Criar pedido - empresa_id={payload.empresa_id}, mesa_id={payload.mesa_id}")

    produtos_payload = ProdutosPedidoRequest(itens=list(payload.itens or []))

    create_payload = PedidoCreateRequest(
        empresa_id=payload.empresa_id,
        cliente_id=payload.cliente_id,
        mesa_codigo=str(payload.mesa_id),
        observacao_geral=payload.observacoes,
        num_pessoas=payload.num_pessoas,
        produtos=produtos_payload,
        tipo_pedido=TipoPedidoCheckoutEnum.MESA,
    )

    return await svc_admin.criar_pedido(create_payload)


@router.get(
    "/mesa",
    response_model=List[PedidoResponseCompleto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_mesa(
    request: Request,
    response: Response,
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    mesa_id: Optional[int] = Query(None, description="ID da mesa para filtrar"),
    apenas_abertos: bool = Query(True, description="Listar apenas pedidos abertos"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Lista pedidos de mesa.
    
    - **empresa_id**: ID da empresa (obrigatório)
    - **mesa_id**: ID da mesa para filtrar (opcional)
    - **apenas_abertos**: Se True, lista apenas pedidos abertos (padrão: True)
    """
    logger.info(f"[Pedidos Mesa] Listar - empresa_id={empresa_id}, mesa_id={mesa_id}, apenas_abertos={apenas_abertos}")

    _emit_v2_warning(
        response,
        request,
        request.url.path,
        "/api/pedidos/admin/v2",
    )

    mesa_service = svc_admin.mesa_service
    if apenas_abertos:
        return mesa_service.list_pedidos_abertos(empresa_id=empresa_id, mesa_id=mesa_id)
    return mesa_service.list_pedidos_abertos(empresa_id=empresa_id, mesa_id=mesa_id)


@router.get(
    "/mesa/{mesa_id}/finalizados",
    response_model=List[PedidoResponseCompleto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_finalizados_mesa(
    request: Request,
    response: Response,
    mesa_id: int = Path(..., description="ID da mesa", gt=0),
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    data_filtro: Optional[date] = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Lista pedidos finalizados de uma mesa específica.
    
    - **mesa_id**: ID da mesa (obrigatório)
    - **empresa_id**: ID da empresa (obrigatório)
    - **data_filtro**: Filtrar por data específica (opcional)
    """
    logger.info(f"[Pedidos Mesa] Listar finalizados - mesa_id={mesa_id}, empresa_id={empresa_id}, data={data_filtro}")
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/mesa/{mesa_id}/finalizados",
    )

    return svc_admin.mesa_service.list_pedidos_finalizados(
        mesa_id=mesa_id,
        data_filtro=data_filtro,
        empresa_id=empresa_id,
    )


@router.get(
    "/mesa/cliente/{cliente_id}",
    response_model=List[PedidoResponseCompleto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_mesa_por_cliente(
    request: Request,
    response: Response,
    cliente_id: int = Path(..., description="ID do cliente", gt=0),
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Lista pedidos de mesa de um cliente específico.
    
    - **cliente_id**: ID do cliente (obrigatório)
    - **empresa_id**: ID da empresa (obrigatório)
    - **skip**: Número de registros para pular (padrão: 0)
    - **limit**: Limite de registros (padrão: 50, máximo: 200)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2?cliente_id={cliente_id}&tipo=MESA",
    )

    logger.info(f"[Pedidos Mesa] Listar por cliente - cliente_id={cliente_id}, empresa_id={empresa_id}")
    return svc_admin.mesa_service.list_pedidos_by_cliente(
        cliente_id=cliente_id,
        empresa_id=empresa_id,
        skip=skip,
        limit=limit,
    )


@router.put(
    "/mesa/{pedido_id}/adicionar-item",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def adicionar_item_pedido_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarItemRequest = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Adiciona um item a um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **produto_cod_barras**: Código de barras do produto (obrigatório)
    - **quantidade**: Quantidade do item (obrigatório)
    - **observacao**: Observação do item (opcional)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/itens",
    )

    logger.info(f"[Pedidos Mesa] Adicionar item - pedido_id={pedido_id}")
    return svc_admin.mesa_service.adicionar_item(pedido_id, body)


@router.put(
    "/mesa/{pedido_id}/adicionar-produto-generico",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def adicionar_produto_generico_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarProdutoGenericoRequest = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Adiciona um produto genérico (produto, receita ou combo) a um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **produto_cod_barras**: Código de barras do produto (opcional)
    - **receita_id**: ID da receita (opcional)
    - **combo_id**: ID do combo (opcional)
    - **quantidade**: Quantidade (obrigatório)
    - **observacao**: Observação (opcional)
    - **adicionais**: Lista de adicionais (opcional)
    - **adicionais_ids**: Lista de IDs de adicionais (opcional)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/itens",
    )

    logger.info(f"[Pedidos Mesa] Adicionar produto genérico - pedido_id={pedido_id}")
    return svc_admin.mesa_service.adicionar_produto_generico(pedido_id, body)


@router.put(
    "/mesa/{pedido_id}/observacoes",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_observacoes_pedido_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: AtualizarObservacoesRequest = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Atualiza as observações de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **observacoes**: Nova observação do pedido
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/observacoes",
    )

    logger.info(f"[Pedidos Mesa] Atualizar observações - pedido_id={pedido_id}")
    patch_payload = PedidoObservacaoPatchRequest(observacoes=payload.observacoes)
    return svc_admin.atualizar_observacoes(pedido_id, patch_payload)


@router.put(
    "/mesa/{pedido_id}/status",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_status_pedido_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: AtualizarStatusPedidoRequest = Body(...),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Atualiza o status de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **status**: Novo status do pedido
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/status",
    )

    logger.info(f"[Pedidos Mesa] Atualizar status - pedido_id={pedido_id}, status={payload.status}")
    patch_payload = PedidoStatusPatchRequest(status=payload.status)
    return svc_admin.atualizar_status(pedido_id, patch_payload)


@router.put(
    "/mesa/{pedido_id}/fechar-conta",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def fechar_conta_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: Optional[FecharContaMesaRequest] = Body(None),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Fecha a conta de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **troco_para**: Valor do troco (opcional)
    - **meio_pagamento_id**: ID do meio de pagamento (opcional)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/fechar-conta",
    )

    logger.info(f"[Pedidos Mesa] Fechar conta - pedido_id={pedido_id}")
    patch_payload = (
        PedidoFecharContaRequest(**payload.model_dump())
        if payload is not None
        else None
    )
    return svc_admin.fechar_conta(pedido_id, patch_payload)


@router.put(
    "/mesa/{pedido_id}/reabrir",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def reabrir_pedido_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Reabre um pedido de mesa cancelado ou entregue.
    
    - **pedido_id**: ID do pedido (obrigatório)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/reabrir",
    )

    logger.info(f"[Pedidos Mesa] Reabrir pedido - pedido_id={pedido_id}")
    return svc_admin.reabrir(pedido_id)


@router.delete(
    "/mesa/{pedido_id}/item/{item_id}",
    response_model=RemoverItemResponse,
    status_code=status.HTTP_200_OK,
)
def remover_item_pedido_mesa(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item_id: int = Path(..., description="ID do item", gt=0),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Remove um item de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **item_id**: ID do item a ser removido (obrigatório)
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/itens/{item_id}",
    )

    logger.info(f"[Pedidos Mesa] Remover item - pedido_id={pedido_id}, item_id={item_id}")
    return svc_admin.mesa_service.remover_item(pedido_id, item_id)


# ======================================================================
# ====================== ENTREGADOR (GERAL) ============================
# ======================================================================
@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def vincular_entregador(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    entregador_id: int | None = Query(None, description="ID do entregador (omita ou envie null para desvincular)"),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Vincula ou desvincula um entregador a um pedido (Delivery).
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    - **entregador_id**: ID do entregador para vincular ou null/omitido para desvincular
    
    Para vincular: envie entregador_id com o ID do entregador (deve ser > 0)
    Para desvincular: envie entregador_id como null ou omita o parâmetro
    
    **Validações:**
    - Pedido deve existir
    - Entregador deve existir (se fornecido)
    - Entregador deve estar vinculado à empresa do pedido
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/entregador",
    )

    logger.info(f"[Pedidos] Vincular entregador - pedido_id={pedido_id} -> entregador_id={entregador_id}")
    
    if entregador_id is not None and entregador_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entregador_id inválido"
        )
    
    request = PedidoEntregadorRequest(entregador_id=entregador_id)
    return svc_admin.atualizar_entregador(pedido_id, request)


@router.delete(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def desvincular_entregador(
    request: Request,
    response: Response,
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    svc_admin: PedidoAdminService = Depends(get_pedido_admin_service),
):
    """
    Desvincula o entregador atual de um pedido.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Remove a vinculação do entregador com o pedido.
    """
    _emit_v2_warning(
        response,
        request,
        request.url.path,
        f"/api/pedidos/admin/v2/{pedido_id}/entregador",
    )

    logger.info(f"[Pedidos] Desvincular entregador - pedido_id={pedido_id}")
    
    return svc_admin.remover_entregador(pedido_id)

"""
Router unificado de pedidos para admin.
Agora todos os tipos de pedidos (Delivery, Mesa, Balcão) usam a mesma tabela unificada.
Todos os endpoints estão centralizados aqui.
"""
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session

from app.api.pedidos.schemas.schema_pedido import (
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoTotal,
    EditarPedidoRequest,
    ItemPedidoEditar,
    KanbanAgrupadoResponse,
    FinalizarPedidoRequest,
)
from app.api.pedidos.schemas.schema_pedido_status_historico import (
    AlterarStatusPedidoBody,
    HistoricoDoPedidoResponse,
    PedidoStatusHistoricoOut,
)
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.dependencies import get_pedido_service
from app.api.pedidos.services.service_pedidos_mesa import (
    PedidoMesaService,
    PedidoMesaCreate,
    AdicionarItemRequest,
    AdicionarProdutoGenericoRequest,
    RemoverItemResponse,
    FecharContaMesaRequest,
    AtualizarObservacoesRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.cadastros.contracts.dependencies import (
    get_produto_contract,
    get_adicional_contract,
    get_combo_contract,
)
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega, PedidoUnificadoModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.cadastros.models.user_model import UserModel
from app.utils.logger import logger
from sqlalchemy import and_, or_
from datetime import datetime

router = APIRouter(
    prefix="/api/pedidos/admin",
    tags=["Admin - Pedidos Unificados"],
    dependencies=[Depends(get_current_user)]
)


def get_mesa_service(
    db: Session = Depends(get_db),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoMesaService:
    """Dependency para obter o serviço de pedidos de mesa"""
    return PedidoMesaService(
        db,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        combo_contract=combo_contract,
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
    db: Session = Depends(get_db),
    date_filter: date = Query(..., description="Filtrar pedidos por data (YYYY-MM-DD) - OBRIGATÓRIO"),
    empresa_id: int = Query(..., description="ID da empresa para filtrar pedidos", gt=0),
    limit: int = Query(500, ge=1, le=1000),
    svc: PedidoService = Depends(get_pedido_service),
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
    logger.info(f"[Pedidos] Listar Kanban - empresa_id={empresa_id}, date_filter={date_filter}")
    pedidos = svc.list_all_kanban(
        date_filter=date_filter,
        empresa_id=empresa_id,
        limit=limit,
    )
    return pedidos


# ======================================================================
# ====================== PEDIDOS GERAIS ===============================
# ======================================================================
@router.get(
    "/{pedido_id}",
    response_model=PedidoResponseCompletoTotal,
    status_code=status.HTTP_200_OK,
)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Busca um pedido específico com informações completas (admin).
    Funciona para todos os tipos: Delivery, Mesa e Balcão.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Retorna todos os dados do pedido incluindo itens, cliente, endereço, etc.
    """
    logger.info(f"[Pedidos] Buscar pedido - pedido_id={pedido_id}")
    
    pedido = svc.get_pedido_by_id_completo_total(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return pedido


@router.get(
    "/{pedido_id}/historico",
    response_model=HistoricoDoPedidoResponse,
    status_code=status.HTTP_200_OK,
)
def obter_historico_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Obtém o histórico completo de alterações de status de um pedido.
    Funciona para todos os tipos: Delivery, Mesa e Balcão.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Retorna todos os registros de mudança de status com timestamps, motivos e observações.
    """
    logger.info(f"[Pedidos] Obter histórico - pedido_id={pedido_id}")
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    # Busca o histórico do pedido usando modelo unificado
    from app.api.pedidos.models.model_pedido_historico_unificado import PedidoHistoricoUnificadoModel
    historicos = (
        db.query(PedidoHistoricoUnificadoModel)
        .filter(PedidoHistoricoUnificadoModel.pedido_id == pedido_id)
        .order_by(PedidoHistoricoUnificadoModel.created_at.desc())
        .all()
    )
    
    # Helper para converter status (string ou enum) para PedidoStatusEnum
    def parse_status(status_value):
        """Helper para converter status (string ou enum) para PedidoStatusEnum."""
        if status_value is None:
            return None
        if isinstance(status_value, str):
            return PedidoStatusEnum(status_value)
        if hasattr(status_value, 'value'):
            return PedidoStatusEnum(status_value.value)
        return PedidoStatusEnum(status_value)
    
    historicos_response = []
    for h in historicos:
        status_anterior = parse_status(h.status_anterior)
        status_novo = parse_status(h.status_novo)
        tipo_operacao_val = h.tipo_operacao.value if h.tipo_operacao and hasattr(h.tipo_operacao, 'value') else (h.tipo_operacao if h.tipo_operacao else None)
        
        historicos_response.append(
            PedidoStatusHistoricoOut(
                id=h.id,
                pedido_id=h.pedido_id,
                status=status_novo or status_anterior,
                status_anterior=status_anterior,
                status_novo=status_novo,
                tipo_operacao=tipo_operacao_val,
                descricao=h.descricao,
                motivo=h.motivo,
                observacoes=h.observacoes,
                criado_em=h.created_at,
                criado_por=h.usuario.username if h.usuario and hasattr(h.usuario, 'username') else None,
                usuario_id=h.usuario_id,
                cliente_id=h.cliente_id,
                ip_origem=h.ip_origem,
                user_agent=h.user_agent,
            )
        )
    
    return HistoricoDoPedidoResponse(
        pedido_id=pedido_id,
        historicos=historicos_response
    )


@router.put(
    "/{pedido_id}/status",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    novo_status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
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
    logger.info(f"[Pedidos] Atualizar status - pedido_id={pedido_id} -> {novo_status} (user={current_user.id})")
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=novo_status, user_id=current_user.id)


@router.delete(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def cancelar_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Cancela um pedido (Delivery, Mesa ou Balcão).
    
    - **pedido_id**: ID do pedido (obrigatório)
    
    **Nota:** Este endpoint cancela o pedido (status CANCELADO).
    """
    logger.info(f"[Pedidos] Cancelar pedido - pedido_id={pedido_id} (user={current_user.id})")
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=PedidoStatusEnum.C, user_id=current_user.id)


# ======================================================================
# ====================== DELIVERY ======================================
# ======================================================================
@router.post(
    "/delivery",
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
    if not hasattr(payload, 'cliente_id') or payload.cliente_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "cliente_id é obrigatório para criar pedido de delivery via admin"
        )
    
    # Converte cliente_id para int se for string
    cliente_id = int(payload.cliente_id) if isinstance(payload.cliente_id, str) else payload.cliente_id
    
    return await svc.finalizar_pedido(payload, cliente_id=cliente_id)


@router.get(
    "/delivery",
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
    "/delivery/cliente/{cliente_id}",
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_delivery_por_cliente(
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


@router.put(
    "/delivery/{pedido_id}",
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
    
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.editar_pedido_parcial(pedido_id, payload)


@router.put(
    "/delivery/{pedido_id}/itens",
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
    
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.atualizar_item_pedido(pedido_id, item)


@router.put(
    "/delivery/{pedido_id}/entregador",
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
    
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.vincular_entregador(pedido_id, entregador_id)


@router.delete(
    "/delivery/{pedido_id}/entregador",
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
    
    if pedido.tipo_entrega != TipoEntrega.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pedido {pedido_id} não é um pedido de delivery"
        )
    
    return svc.desvincular_entregador(pedido_id)


# ======================================================================
# ====================== MESA =========================================
# ======================================================================
@router.post(
    "/mesa",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_201_CREATED,
)
def criar_pedido_mesa(
    payload: PedidoMesaCreate = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
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
    logger.info(f"[Pedidos Mesa] Criar pedido - empresa_id={payload.empresa_id}, mesa_id={payload.mesa_id}")
    return svc.criar_pedido(payload)


@router.get(
    "/mesa",
    response_model=List[PedidoResponseCompleto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_mesa(
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    mesa_id: Optional[int] = Query(None, description="ID da mesa para filtrar"),
    apenas_abertos: bool = Query(True, description="Listar apenas pedidos abertos"),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Lista pedidos de mesa.
    
    - **empresa_id**: ID da empresa (obrigatório)
    - **mesa_id**: ID da mesa para filtrar (opcional)
    - **apenas_abertos**: Se True, lista apenas pedidos abertos (padrão: True)
    """
    logger.info(f"[Pedidos Mesa] Listar - empresa_id={empresa_id}, mesa_id={mesa_id}, apenas_abertos={apenas_abertos}")
    
    if apenas_abertos:
        return svc.list_pedidos_abertos(empresa_id=empresa_id, mesa_id=mesa_id)
    else:
        return svc.list_pedidos_abertos(empresa_id=empresa_id, mesa_id=mesa_id)


@router.get(
    "/mesa/{mesa_id}/finalizados",
    response_model=List[PedidoResponseCompleto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_finalizados_mesa(
    mesa_id: int = Path(..., description="ID da mesa", gt=0),
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    data_filtro: Optional[date] = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Lista pedidos finalizados de uma mesa específica.
    
    - **mesa_id**: ID da mesa (obrigatório)
    - **empresa_id**: ID da empresa (obrigatório)
    - **data_filtro**: Filtrar por data específica (opcional)
    """
    logger.info(f"[Pedidos Mesa] Listar finalizados - mesa_id={mesa_id}, empresa_id={empresa_id}, data={data_filtro}")
    return svc.list_pedidos_finalizados(mesa_id=mesa_id, data_filtro=data_filtro, empresa_id=empresa_id)


@router.get(
    "/mesa/cliente/{cliente_id}",
    response_model=List[PedidoResponseCompleto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_mesa_por_cliente(
    cliente_id: int = Path(..., description="ID do cliente", gt=0),
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(50, ge=1, le=200, description="Limite de registros"),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Lista pedidos de mesa de um cliente específico.
    
    - **cliente_id**: ID do cliente (obrigatório)
    - **empresa_id**: ID da empresa (obrigatório)
    - **skip**: Número de registros para pular (padrão: 0)
    - **limit**: Limite de registros (padrão: 50, máximo: 200)
    """
    logger.info(f"[Pedidos Mesa] Listar por cliente - cliente_id={cliente_id}, empresa_id={empresa_id}")
    return svc.list_pedidos_by_cliente(cliente_id=cliente_id, empresa_id=empresa_id, skip=skip, limit=limit)


@router.put(
    "/mesa/{pedido_id}/adicionar-item",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def adicionar_item_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarItemRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Adiciona um item a um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **produto_cod_barras**: Código de barras do produto (obrigatório)
    - **quantidade**: Quantidade do item (obrigatório)
    - **observacao**: Observação do item (opcional)
    """
    logger.info(f"[Pedidos Mesa] Adicionar item - pedido_id={pedido_id}")
    return svc.adicionar_item(pedido_id, body)


@router.put(
    "/mesa/{pedido_id}/adicionar-produto-generico",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def adicionar_produto_generico_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarProdutoGenericoRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
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
    logger.info(f"[Pedidos Mesa] Adicionar produto genérico - pedido_id={pedido_id}")
    return svc.adicionar_produto_generico(pedido_id, body)


@router.put(
    "/mesa/{pedido_id}/observacoes",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_observacoes_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: AtualizarObservacoesRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Atualiza as observações de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **observacoes**: Nova observação do pedido
    """
    logger.info(f"[Pedidos Mesa] Atualizar observações - pedido_id={pedido_id}")
    return svc.atualizar_observacoes(pedido_id, payload)


@router.put(
    "/mesa/{pedido_id}/status",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def atualizar_status_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: AtualizarStatusPedidoRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Atualiza o status de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **status**: Novo status do pedido
    """
    logger.info(f"[Pedidos Mesa] Atualizar status - pedido_id={pedido_id}, status={payload.status}")
    return svc.atualizar_status(pedido_id, payload)


@router.put(
    "/mesa/{pedido_id}/fechar-conta",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def fechar_conta_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: Optional[FecharContaMesaRequest] = Body(None),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Fecha a conta de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **troco_para**: Valor do troco (opcional)
    - **meio_pagamento_id**: ID do meio de pagamento (opcional)
    """
    logger.info(f"[Pedidos Mesa] Fechar conta - pedido_id={pedido_id}")
    return svc.fechar_conta(pedido_id, payload)


@router.put(
    "/mesa/{pedido_id}/reabrir",
    response_model=PedidoResponseCompleto,
    status_code=status.HTTP_200_OK,
)
def reabrir_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Reabre um pedido de mesa cancelado ou entregue.
    
    - **pedido_id**: ID do pedido (obrigatório)
    """
    logger.info(f"[Pedidos Mesa] Reabrir pedido - pedido_id={pedido_id}")
    return svc.reabrir(pedido_id)


@router.delete(
    "/mesa/{pedido_id}/item/{item_id}",
    response_model=RemoverItemResponse,
    status_code=status.HTTP_200_OK,
)
def remover_item_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item_id: int = Path(..., description="ID do item", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Remove um item de um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    - **item_id**: ID do item a ser removido (obrigatório)
    """
    logger.info(f"[Pedidos Mesa] Remover item - pedido_id={pedido_id}, item_id={item_id}")
    return svc.remover_item(pedido_id, item_id)


# ======================================================================
# ====================== ENTREGADOR (GERAL) ============================
# ======================================================================
@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def vincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    entregador_id: int | None = Query(None, description="ID do entregador (omita ou envie null para desvincular)"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
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
    logger.info(f"[Pedidos] Vincular entregador - pedido_id={pedido_id} -> entregador_id={entregador_id}")
    
    # Valida entregador_id se fornecido
    if entregador_id is not None and entregador_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entregador_id deve ser maior que 0 quando fornecido"
        )
    
    return svc.vincular_entregador(pedido_id, entregador_id)


@router.delete(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
)
def desvincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Desvincula o entregador atual de um pedido.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    
    Remove a vinculação do entregador com o pedido.
    """
    logger.info(f"[Pedidos] Desvincular entregador - pedido_id={pedido_id}")
    
    # Verifica se o pedido existe
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido com ID {pedido_id} não encontrado"
        )
    
    return svc.desvincular_entregador(pedido_id)

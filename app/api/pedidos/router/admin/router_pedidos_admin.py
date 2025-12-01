from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session

from app.api.pedidos.schemas.schema_pedido import (
    PedidoResponse,
    PedidoResponseCompletoTotal,
    EditarPedidoRequest,
    ItemPedidoEditar,
    KanbanAgrupadoResponse,
)
from app.api.pedidos.schemas.schema_pedido_status_historico import (
    AlterarStatusPedidoBody,
    HistoricoDoPedidoResponse,
    PedidoStatusHistoricoOut,
)
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.dependencies import get_pedido_service
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.cadastros.models.user_model import UserModel
from app.utils.logger import logger

router = APIRouter(prefix="/api/pedidos/admin", tags=["Admin - Pedidos"], dependencies=[Depends(get_current_user)])

# ======================================================================
# ============================ KANBAN ==================================
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
# ===================== GET PEDIDO BY ID ===============================
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

# ======================================================================
# ================= OBTER HISTÓRICO DO PEDIDO ==========================
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

# ======================================================================
# ==================== ATUALIZA STATUS PEDIDO  ========================
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
    Atualiza o status de um pedido de delivery (somente admin).
    
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

# ======================================================================
# ================= VINCULAR/DESVINCULAR ENTREGADOR ====================
@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)#
def vincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    entregador_id: int | None = Query(None, description="ID do entregador (omita ou envie null para desvincular)"),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Vincula ou desvincula um entregador a um pedido de delivery.
    
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


# ======================================================================
# ================= DESVINCULAR ENTREGADOR ============================
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

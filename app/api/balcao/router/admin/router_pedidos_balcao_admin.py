from fastapi import APIRouter, Depends, Path, status, Query, Body
from sqlalchemy.orm import Session
from datetime import date

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoCreate,
    PedidoBalcaoOut,
    AdicionarItemRequest,
    RemoverItemResponse,
    FecharContaBalcaoRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.balcao.schemas.schema_pedido_balcao_historico import HistoricoPedidoBalcaoResponse
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service
from app.api.cadastros.models.user_model import UserModel


router = APIRouter(
    prefix="/api/balcao/admin/pedidos",
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=PedidoBalcaoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar pedido de balcão",
    description="""
    Cria um novo pedido de balcão. 
    
    **Características:**
    - `mesa_id` é opcional (pode criar pedido sem mesa)
    - Pode ou não ter `cliente_id` associado
    - Permite adicionar itens durante a criação
    
    **Status inicial:** PENDENTE
    """,
    responses={
        201: {"description": "Pedido criado com sucesso"},
        400: {"description": "Dados inválidos ou produto não encontrado"},
        404: {"description": "Mesa não encontrada (se mesa_id informado)"}
    }
)
def criar_pedido(body: PedidoBalcaoCreate, db: Session = Depends(get_db), svc: PedidoBalcaoService = Depends(get_pedido_balcao_service)):
    """Cria um novo pedido de balcão"""
    return svc.criar_pedido(body)


@router.post(
    "/{pedido_id:int}/itens",
    response_model=PedidoBalcaoOut,
    summary="Adicionar item ao pedido",
    description="""
    Adiciona um novo item ao pedido de balcão.
    
    **Validações:**
    - Pedido deve estar aberto (não pode ser CANCELADO ou ENTREGUE)
    - Produto deve existir e estar disponível
    - Quantidade deve ser maior que zero
    
    **Atualização automática:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Item adicionado com sucesso"},
        400: {"description": "Pedido fechado/cancelado ou dados inválidos"},
        404: {"description": "Pedido ou produto não encontrado"}
    }
)
def adicionar_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarItemRequest = Body(..., description="Dados do item a ser adicionado"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Adiciona um item ao pedido de balcão"""
    return svc.adicionar_item(pedido_id, body, usuario_id=current_user.id)


@router.delete(
    "/{pedido_id:int}/itens/{item_id:int}",
    response_model=RemoverItemResponse,
    summary="Remover item do pedido",
    description="""
    Remove um item específico do pedido de balcão.
    
    **Validações:**
    - Pedido deve estar aberto (não pode ser CANCELADO ou ENTREGUE)
    - Item deve existir no pedido
    
    **Atualização automática:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Item removido com sucesso"},
        400: {"description": "Pedido fechado/cancelado"},
        404: {"description": "Pedido ou item não encontrado"}
    }
)
def remover_item(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    item_id: int = Path(..., description="ID do item a ser removido", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Remove um item do pedido de balcão"""
    return svc.remover_item(pedido_id, item_id, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/cancelar",
    response_model=PedidoBalcaoOut,
    summary="Cancelar pedido",
    description="""
    Cancela um pedido de balcão, alterando seu status para CANCELADO.
    
    **Observação:** Pedidos cancelados não podem ser modificados.
    """,
    responses={
        200: {"description": "Pedido cancelado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def cancelar_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser cancelado", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Cancela um pedido de balcão"""
    return svc.cancelar(pedido_id, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/fechar-conta",
    response_model=PedidoBalcaoOut,
    summary="Fechar conta do pedido",
    description="""
    Fecha a conta de um pedido de balcão, alterando seu status para ENTREGUE.
    
    **Informações de pagamento (opcional):**
    - `meio_pagamento_id`: ID do meio de pagamento utilizado
    - `troco_para`: Valor para o qual deseja troco (apenas para pagamento em dinheiro)
    
    **Observação:** As informações de pagamento são salvas nas observações do pedido.
    """,
    responses={
        200: {"description": "Conta fechada com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def fechar_conta_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    payload: FecharContaBalcaoRequest | None = Body(
        default=None,
        description="Dados de pagamento (opcional)"
    ),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Fecha a conta de um pedido de balcão"""
    return svc.fechar_conta(pedido_id, payload, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/abrir",
    response_model=PedidoBalcaoOut,
    summary="Abrir pedido",
    description="""
    Atalho para reabrir um pedido de balcão que foi encerrado (ENTREGUE ou CANCELADO).
    
    O pedido volta para o fluxo de produção (status CONFIRMADO/EM IMPRESSÃO).
    """,
    responses={
        200: {"description": "Pedido aberto com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def abrir_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser reaberto", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Reabre um pedido de balcão (atalho para /reabrir)."""
    return svc.reabrir(pedido_id, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/fechar",
    response_model=PedidoBalcaoOut,
    summary="Fechar pedido",
    description="""
    Atalho para fechar a conta de um pedido de balcão, alterando o status para ENTREGUE.

    Aceita as mesmas informações de pagamento opcionais do endpoint `/fechar-conta`.
    """,
    responses={
        200: {"description": "Pedido fechado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def fechar_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser fechado", gt=0),
    payload: FecharContaBalcaoRequest | None = Body(
        default=None,
        description="Dados de pagamento (opcional)"
    ),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Fecha a conta de um pedido de balcão (atalho)."""
    return svc.fechar_conta(pedido_id, payload, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/reabrir",
    response_model=PedidoBalcaoOut,
    summary="Reabrir pedido",
    description="""
    Reabre um pedido que foi cancelado ou entregue, alterando seu status para CONFIRMADO.
    
    **Validação:** Apenas pedidos com status CANCELADO ou ENTREGUE podem ser reabertos.
    """,
    responses={
        200: {"description": "Pedido reaberto com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def reabrir_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser reaberto", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Reabre um pedido de balcão cancelado ou entregue"""
    return svc.reabrir(pedido_id, usuario_id=current_user.id)


@router.post(
    "/{pedido_id:int}/confirmar",
    response_model=PedidoBalcaoOut,
    summary="Confirmar pedido",
    description="""
    Confirma um pedido de balcão, alterando seu status de PENDENTE para EM IMPRESSÃO.
    
    **Fluxo de status (sem o estágio 'Saiu para entrega'):**
    - PENDENTE → EM IMPRESSÃO → EM PREPARO → ENTREGUE
    
    **Observação:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Pedido confirmado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def confirmar_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser confirmado", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Confirma um pedido de balcão"""
    return svc.confirmar(pedido_id, usuario_id=current_user.id)


@router.patch(
    "/{pedido_id:int}/status",
    response_model=PedidoBalcaoOut,
    summary="Atualizar status do pedido",
    description="""
    Atualiza manualmente o status de um pedido de balcão.

    **Observações:**
    - Para definir status ENTREGUE ou CANCELADO utilize esta rota ou as operações específicas.
    """
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AtualizarStatusPedidoRequest = Body(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Atualiza o status de um pedido de balcão"""
    return svc.atualizar_status(pedido_id, body, usuario_id=current_user.id)


# -------- Consultas --------
@router.get(
    "/{pedido_id:int}",
    response_model=PedidoBalcaoOut,
    summary="Buscar pedido por ID",
    description="""
    Busca um pedido de balcão específico pelo ID.
    
    **Retorna:**
    - Informações completas do pedido
    - Lista de itens do pedido
    - Status atual
    - Valor total
    - Dados do cliente (se associado)
    - Mesa (se associada)
    """,
    responses={
        200: {"description": "Pedido encontrado"},
        404: {"description": "Pedido não encontrado"}
    }
)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Busca um pedido de balcão por ID"""
    return svc.get_pedido(pedido_id)


@router.get(
    "",
    response_model=list[PedidoBalcaoOut],
    summary="Listar pedidos abertos",
    description="""
    Lista todos os pedidos de balcão que estão abertos (não finalizados).
    
    **Status considerados abertos:**
    - PENDENTE
    - EM IMPRESSÃO
    - EM PREPARO
    - EDITADO / EM EDIÇÃO / AGUARDANDO PAGAMENTO
    
    **Ordenação:** Pedidos mais recentes primeiro.
    """,
    responses={
        200: {"description": "Lista de pedidos abertos"}
    }
)
def list_pedidos_abertos(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Lista todos os pedidos de balcão abertos"""
    return svc.list_pedidos_abertos(empresa_id=empresa_id)


@router.get(
    "/finalizados",
    response_model=list[PedidoBalcaoOut],
    summary="Listar pedidos finalizados",
    description="""
    Lista todos os pedidos de balcão que foram finalizados (status ENTREGUE).
    
    **Filtros disponíveis:**
    - `data`: Filtra por data específica (YYYY-MM-DD). Se não informado, retorna todos os pedidos finalizados.
    
    **Ordenação:** Pedidos mais recentes primeiro.
    """,
    responses={
        200: {"description": "Lista de pedidos finalizados"}
    }
)
def list_pedidos_finalizados(
    data: date | None = Query(
        None,
        description="Filtrar por data (YYYY-MM-DD). Se não informado, retorna todos os pedidos finalizados"
    ),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Retorna todos os pedidos finalizados (ENTREGUE), opcionalmente filtrados por data"""
    return svc.list_pedidos_finalizados(data, empresa_id=empresa_id)


@router.get(
    "/{pedido_id:int}/historico",
    response_model=HistoricoPedidoBalcaoResponse,
    summary="Obter histórico do pedido",
    description="""
    Obtém o histórico completo de alterações de um pedido de balcão.
    
    **Retorna:**
    - Todas as operações realizadas no pedido
    - Alterações de status
    - Adição/remoção de itens
    - Informações de quem executou cada operação
    - Timestamps de cada operação
    
    **Ordenação:** Operações mais recentes primeiro.
    """,
    responses={
        200: {"description": "Histórico retornado com sucesso"},
        404: {"description": "Pedido não encontrado"}
    }
)
def obter_historico_pedido(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros de histórico"),
    db: Session = Depends(get_db),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Obtém o histórico completo de um pedido de balcão"""
    return svc.get_historico(pedido_id, limit=limit)



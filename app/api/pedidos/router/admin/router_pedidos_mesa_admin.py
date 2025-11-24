from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session

from app.api.pedidos.services.service_pedidos_mesa import PedidoMesaService
from app.api.mesas.schemas.schema_pedido_mesa import (
    PedidoMesaCreate,
    PedidoMesaOut,
    AdicionarItemRequest,
    AdicionarProdutoGenericoRequest,
    RemoverItemResponse,
    StatusPedidoMesaEnum,
    FecharContaMesaRequest,
    AtualizarObservacoesRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.cadastros.contracts.dependencies import (
    get_produto_contract,
    get_adicional_contract,
    get_combo_contract,
)
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.cadastros.models.user_model import UserModel
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/pedidos/admin/mesa",
    tags=["Admin - Pedidos Mesa"],
    dependencies=[Depends(get_current_user)],
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
# ============================ CREATE ==================================
# ======================================================================
@router.post(
    "/",
    response_model=PedidoMesaOut,
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


# ======================================================================
# ============================ READ ====================================
# ======================================================================
@router.get(
    "/",
    response_model=List[PedidoMesaOut],
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
        # Para listar todos, precisamos de uma implementação adicional
        # Por enquanto, retornamos apenas os abertos
        return svc.list_pedidos_abertos(empresa_id=empresa_id, mesa_id=mesa_id)


@router.get(
    "/{pedido_id}",
    response_model=PedidoMesaOut,
    status_code=status.HTTP_200_OK,
)
def obter_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Obtém um pedido de mesa específico por ID.
    
    - **pedido_id**: ID do pedido (obrigatório, deve ser maior que 0)
    """
    logger.info(f"[Pedidos Mesa] Obter pedido - pedido_id={pedido_id}")
    return svc.get_pedido(pedido_id)


@router.get(
    "/mesa/{mesa_id}/finalizados",
    response_model=List[PedidoMesaOut],
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
    "/cliente/{cliente_id}",
    response_model=List[PedidoMesaOut],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_por_cliente(
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


# ======================================================================
# ============================ UPDATE ==================================
# ======================================================================
@router.put(
    "/{pedido_id}/adicionar-item",
    response_model=PedidoMesaOut,
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
    "/{pedido_id}/adicionar-produto-generico",
    response_model=PedidoMesaOut,
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
    "/{pedido_id}/observacoes",
    response_model=PedidoMesaOut,
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
    "/{pedido_id}/status",
    response_model=PedidoMesaOut,
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
    "/{pedido_id}/fechar-conta",
    response_model=PedidoMesaOut,
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
    "/{pedido_id}/reabrir",
    response_model=PedidoMesaOut,
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


# ======================================================================
# ============================ DELETE ==================================
# ======================================================================
@router.delete(
    "/{pedido_id}/item/{item_id}",
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


@router.delete(
    "/{pedido_id}",
    response_model=PedidoMesaOut,
    status_code=status.HTTP_200_OK,
)
def cancelar_pedido_mesa(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_mesa_service),
):
    """
    Cancela um pedido de mesa.
    
    - **pedido_id**: ID do pedido (obrigatório)
    
    **Nota:** Este endpoint cancela o pedido (status CANCELADO).
    """
    logger.info(f"[Pedidos Mesa] Cancelar pedido - pedido_id={pedido_id}")
    return svc.cancelar(pedido_id)


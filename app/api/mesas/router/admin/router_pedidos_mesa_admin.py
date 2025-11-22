from fastapi import APIRouter, Depends, Path, status, Query, Body
from sqlalchemy.orm import Session
from datetime import date

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.mesas.schemas.schema_pedido_mesa import (
    PedidoMesaCreate,
    PedidoMesaOut,
    AdicionarItemRequest,
    AdicionarProdutoGenericoRequest,
    RemoverItemResponse,
    FecharContaMesaRequest,
    AtualizarObservacoesRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.mesas.services.service_pedidos_mesa import PedidoMesaService
from app.api.mesas.services.dependencies import get_pedido_mesa_service


router = APIRouter(
    prefix="/api/mesas/admin/pedidos",
    tags=["Admin - Mesas - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=PedidoMesaOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(body: PedidoMesaCreate, db: Session = Depends(get_db), svc: PedidoMesaService = Depends(get_pedido_mesa_service)):
    return svc.criar_pedido(body)


@router.post("/{pedido_id}/itens", response_model=PedidoMesaOut)
def adicionar_item(
    pedido_id: int = Path(...),
    body: AdicionarItemRequest = None,
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    """⚠️ LEGADO: Use o endpoint /produtos que aceita produtos, receitas e combos"""
    return svc.adicionar_item(pedido_id, body)


@router.post(
    "/{pedido_id}/produtos",
    response_model=PedidoMesaOut,
    summary="Adicionar produto genérico ao pedido",
    description="""
    Adiciona qualquer tipo de produto ao pedido de mesa (produto normal, receita ou combo).
    O sistema identifica automaticamente o tipo baseado nos campos preenchidos.
    
    **Regras de identificação:**
    - Se `produto_cod_barras` estiver presente → Item normal (produto)
    - Se `receita_id` estiver presente → Receita
    - Se `combo_id` estiver presente → Combo
    
    **Validações:**
    - Pedido deve estar aberto (não pode ser CANCELADO ou ENTREGUE)
    - Apenas um tipo de produto deve ser informado
    - Produto/Receita/Combo deve existir e estar disponível
    - Deve pertencer à empresa do pedido
    - Quantidade deve ser maior que zero
    """,
)
def adicionar_produto_generico(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarProdutoGenericoRequest = Body(
        ...,
        description="Dados do produto a ser adicionado (produto, receita ou combo)"
    ),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    """Adiciona um produto genérico (produto, receita ou combo) ao pedido de mesa"""
    return svc.adicionar_produto_generico(pedido_id, body)


@router.delete("/{pedido_id}/itens/{item_id}", response_model=RemoverItemResponse)
def remover_item(
    pedido_id: int = Path(...),
    item_id: int = Path(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    return svc.remover_item(pedido_id, item_id)


@router.post("/{pedido_id}/cancelar", response_model=PedidoMesaOut)
def cancelar_pedido(pedido_id: int = Path(...), db: Session = Depends(get_db), svc: PedidoMesaService = Depends(get_pedido_mesa_service)):
    return svc.cancelar(pedido_id)


@router.post("/{pedido_id}/fechar-conta", response_model=PedidoMesaOut)
def fechar_conta_pedido(
    pedido_id: int = Path(...),
    payload: FecharContaMesaRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    return svc.fechar_conta(pedido_id, payload)


@router.post("/{pedido_id}/reabrir", response_model=PedidoMesaOut)
def reabrir_pedido(pedido_id: int = Path(...), db: Session = Depends(get_db), svc: PedidoMesaService = Depends(get_pedido_mesa_service)):
    return svc.reabrir(pedido_id)


@router.post("/{pedido_id}/confirmar", response_model=PedidoMesaOut)
def confirmar_pedido(pedido_id: int = Path(...), db: Session = Depends(get_db), svc: PedidoMesaService = Depends(get_pedido_mesa_service)):
    return svc.confirmar(pedido_id)


@router.patch(
    "/{pedido_id:int}/status",
    response_model=PedidoMesaOut,
    summary="Atualizar status do pedido",
    description="Atualiza o status de um pedido de mesa."
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido"),
    body: AtualizarStatusPedidoRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    return svc.atualizar_status(pedido_id, body)


# -------- Consultas --------
@router.get("/{pedido_id}", response_model=PedidoMesaOut)
def get_pedido(pedido_id: int = Path(...), db: Session = Depends(get_db), svc: PedidoMesaService = Depends(get_pedido_mesa_service)):
    return svc.get_pedido(pedido_id)


@router.get("", response_model=list[PedidoMesaOut])
def list_pedidos_abertos(
    mesa_id: int | None = Query(None, description="Filtrar por mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    return svc.list_pedidos_abertos(empresa_id=empresa_id, mesa_id=mesa_id)


@router.get("/finalizados/{mesa_id}", response_model=list[PedidoMesaOut])
def list_pedidos_finalizados(
    mesa_id: int = Path(..., description="ID da mesa"),
    data: date | None = Query(None, description="Filtrar por data (YYYY-MM-DD). Se não informado, retorna todos os pedidos finalizados da mesa"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    """Retorna todos os pedidos finalizados (ENTREGUE) da mesa especificada, opcionalmente filtrados por data"""
    return svc.list_pedidos_finalizados(mesa_id, data, empresa_id=empresa_id)


@router.put("/{pedido_id}", response_model=PedidoMesaOut)
def atualizar_observacoes_pedido(
    pedido_id: int = Path(..., description="ID do pedido"),
    body: AtualizarObservacoesRequest = Body(...),
    db: Session = Depends(get_db),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    """Atualiza as observações de um pedido"""
    return svc.atualizar_observacoes(pedido_id, body)



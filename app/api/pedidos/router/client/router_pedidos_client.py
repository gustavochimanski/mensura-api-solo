from typing import List, Union

from fastapi import APIRouter, status, Path, Query, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.pedidos.schemas.schema_pedido import (
    FinalizarPedidoRequest,
    PedidoResponse,
    EditarPedidoRequest,
    ItemPedidoEditar,
    ModoEdicaoRequest,
    PreviewCheckoutResponse,
    TipoPedidoCheckoutEnum,
)
from app.api.pedidos.schemas.schema_pedido_cliente import PedidoClienteListItem
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.dependencies import get_pedido_service
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.api.pedidos.services.service_pedidos_mesa import PedidoMesaService, PedidoMesaCreate
from app.api.pedidos.services.service_pedidos_balcao import PedidoBalcaoService, PedidoBalcaoCreate
from app.api.pedidos.schemas.schema_pedido import (
    PedidoResponse,
    PedidoResponseCompleto,
    ItemPedidoRequest,
)
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.cadastros.contracts.dependencies import get_produto_contract

router = APIRouter(prefix="/api/pedidos/client", tags=["Client - Pedidos"])

# ======================================================================
# ====================== PREVIEW CHECKOUT =============================
@router.post("/checkout/preview", response_model=PreviewCheckoutResponse, status_code=status.HTTP_200_OK)
def preview_checkout(
    payload: FinalizarPedidoRequest = Body(...),
    
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Calcula o preview do checkout (subtotal, taxas, desconto, total)
    sem criar o pedido no banco de dados.
    
    Este endpoint é útil para mostrar ao cliente os valores antes de finalizar o pedido.
    """
    logger.info(f"[Pedidos] Preview checkout solicitado - cliente_id={cliente.id if cliente else None}")
    return svc.calcular_preview_checkout(payload, cliente_id=cliente.id)


@router.post(
    "/checkout",
    response_model=Union[PedidoResponse, PedidoResponseCompleto],
    status_code=status.HTTP_201_CREATED,
)
async def finalizar_checkout(
    payload: FinalizarPedidoRequest = Body(...),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoService = Depends(get_pedido_service),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
):
    """
    Finaliza o checkout criando o pedido no banco de dados.
    """
    logger.info(f"[Pedidos] Finalizar checkout - cliente_id={cliente.id} tipo={payload.tipo_pedido}")

    if payload.tipo_pedido == TipoPedidoCheckoutEnum.DELIVERY:
        return await svc.finalizar_pedido(payload, cliente_id=cliente.id)

    if payload.tipo_pedido == TipoPedidoCheckoutEnum.MESA:
        from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
        complemento_contract = ComplementoAdapter(db)
        mesa_service = PedidoMesaService(
            db, 
            produto_contract=produto_contract,
            complemento_contract=complemento_contract
        )
        try:
            mesa_codigo = int(str(payload.mesa_codigo))
        except (TypeError, ValueError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código da mesa inválido")

        mesa_payload = PedidoMesaCreate(
            empresa_id=payload.empresa_id,
            mesa_id=mesa_codigo,
            cliente_id=cliente.id,
            observacoes=payload.observacao_geral,
            num_pessoas=payload.num_pessoas,
            itens=[
                ItemPedidoRequest(
                    produto_cod_barras=item.produto_cod_barras,
                    quantidade=item.quantidade,
                    observacao=item.observacao,
                )
                for item in (
                    (payload.produtos.itens if payload.produtos and payload.produtos.itens is not None else payload.itens)
                    or []
                )
            ],
        )
        return mesa_service.criar_pedido(mesa_payload)

    if payload.tipo_pedido == TipoPedidoCheckoutEnum.BALCAO:
        from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
        complemento_contract = ComplementoAdapter(db)
        balcao_service = PedidoBalcaoService(
            db, 
            produto_contract=produto_contract,
            complemento_contract=complemento_contract
        )
        mesa_codigo = None
        if payload.mesa_codigo is not None:
            try:
                mesa_codigo = int(str(payload.mesa_codigo))
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código da mesa inválido")

        balcao_payload = PedidoBalcaoCreate(
            empresa_id=payload.empresa_id,
            mesa_id=mesa_codigo,
            cliente_id=cliente.id,
            observacoes=payload.observacao_geral,
            itens=[
                ItemPedidoRequest(
                    produto_cod_barras=item.produto_cod_barras,
                    quantidade=item.quantidade,
                    observacao=item.observacao,
                )
                for item in (
                    (payload.produtos.itens if payload.produtos and payload.produtos.itens is not None else payload.itens)
                    or []
                )
            ],
        )
        return balcao_service.criar_pedido(balcao_payload)

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Tipo de pedido '{payload.tipo_pedido}' não suportado para checkout.",
    )

# ======================================================================
# ====================== LISTAR PEDIDOS  ===============================
@router.get("/", response_model=list[PedidoClienteListItem], status_code=status.HTTP_200_OK)
def listar_pedidos(
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Lista pedidos do cliente mesclando pedidos de delivery, mesa e balcão.
    """
    return svc.listar_pedidos_cliente_unificado(cliente_id=cliente.id, skip=skip, limit=limit)



# ======================================================================
# ===================  ATUALIZA ITENS PEDIDO ===========================
@router.put(
    "/{pedido_id}/itens",
    response_model=PedidoResponse
)
def atualizar_item_cliente(
    pedido_id: int = Path(..., description="ID do pedido"),
    item: ItemPedidoEditar = Body(...),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    Atualiza itens de um pedido do cliente.
    
    - **pedido_id**: ID do pedido
    - **item**: Objeto com a ação a ser executada (adicionar, atualizar, remover)
    """
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    return svc.atualizar_item_pedido(pedido_id, item)

# ======================================================================
# =============== EDITA INFORMAÇÕES GERAIS PEDIDO ======================
# ⚠️ DEPRECATED: Use /api/pedidos/{pedido_id}/editar ao invés deste endpoint
@router.put(
    "/{pedido_id}/editar",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK
)
def atualizar_pedido_cliente(
        pedido_id: int = Path(..., description="ID do pedido a ser atualizado"),
        payload: EditarPedidoRequest = Body(...),
        cliente: ClienteModel = Depends(get_cliente_by_super_token),
        db: Session = Depends(get_db),
        svc: PedidoService = Depends(get_pedido_service),
):
    """
    ⚠️ DEPRECATED: Use o Gateway Orquestrador (/api/pedidos/{pedido_id}/editar)
    
    Este endpoint está sendo substituído pelo Gateway Orquestrador que unifica
    endpoints de admin e client em um único endpoint.
    
    **Recomendado:** Use `PUT /api/pedidos/{pedido_id}/editar`
    
    Este endpoint será mantido apenas para compatibilidade retroativa.
    """
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    if pedido.cliente_id != cliente.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

    return svc.editar_pedido_parcial(pedido_id, payload)

# ======================================================================
# =================== ALTERAR MODO EDIÇÃO =============================
@router.put(
    "/{pedido_id}/modo-edicao",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK
)
def alterar_modo_edicao(
    pedido_id: int = Path(..., description="ID do pedido"),
    payload: ModoEdicaoRequest = Body(...),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db),
    svc: PedidoService = Depends(get_pedido_service),
):
    """
    [DESATIVADO] Altera o modo de edição do pedido.

    True = ativa modo edição (status X), False = finaliza edição (status D).

    A partir de agora, alterações de status de pedido só são permitidas
    em endpoints de admin.
    """
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Alteração de status de pedido é permitida apenas em endpoints de admin.",
    )



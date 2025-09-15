from datetime import date
from typing import List

from app.api.mensura.models.user_model import UserModel
from fastapi import APIRouter, status, Path, Query, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.schemas.schema_pedido import PedidoResponse, PedidoKanbanResponse, \
    EditarPedidoRequest, ItemPedidoEditar, PedidoResponseCompletoTotal, VincularEntregadorRequest
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.delivery.services.pedidos.service_pedido import PedidoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos", tags=["Pedidos"])

# ======================================================================
# ===================== GET PEDIDO BY ID ===============================
@router.get("/{pedido_id}", response_model=PedidoResponseCompletoTotal, status_code=status.HTTP_200_OK)
def get_pedido(
    pedido_id: int = Path(..., description="ID do pedido"), 
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    svc = PedidoService(db)
    return svc.get_pedido_by_id_completo_total(pedido_id)

# ======================================================================
# ============================ KANBAN ==================================
@router.get(
    "/admin/kanban",
    response_model=list[PedidoKanbanResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def listar_pedidos_admin_kanban(
    db: Session = Depends(get_db),
    date_filter: date | None = Query(None, description="Filtrar pedidos por data (YYYY-MM-DD)"),
    empresa_id: int = Query()
):
    """
    Lista pedidos do sistema (para admin, versão resumida pro Kanban)
    """
    return PedidoService(db).list_all_kanban(date_filter=date_filter, empresa_id=empresa_id)


# ======================================================================
# ==================== ATUALIZA STATUS PEDIDO  ========================
@router.put(
    "/status/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_status_pedido(
    pedido_id: int = Path(..., description="ID do pedido"),
    status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
    db: Session = Depends(get_db),
):
    """
    Atualiza o status de um pedido (somente admin).
    """
    logger.info(f"[Pedidos] Atualizar status - pedido_id={pedido_id} -> {status}")
    svc = PedidoService(db)
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=status)


# ======================================================================
# ================= ATUALIZAR INFO GERAL PEDIDO ========================
@router.put(
    "/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_pedido(
        pedido_id: int = Path(..., description="ID do pedido a ser atualizado"),
        payload: EditarPedidoRequest = Body(...),
        db: Session = Depends(get_db),
):
    """
    Atualiza dados de um pedido existente:
    - meio_pagamento_id
    - endereco_id
    - cupom_id
    - observacao_geral
    - troco_para
    - itens
    """
    svc = PedidoService(db)

    # Atualiza o pedido via serviço
    return svc.editar_pedido_parcial(pedido_id, payload)


# ======================================================================
# ==================== ATUALIZAR ITENS PEDIDO ==========================
@router.put("/{pedido_id}/itens", response_model=PedidoResponse)
def atualizar_itens(
    pedido_id: int = Path(..., description="ID do pedido"),
    itens: List[ItemPedidoEditar] = ...,
    db: Session = Depends(get_db),
):
    """
    Atualiza os itens de um pedido: adicionar, atualizar quantidade/observação ou remover.
    """
    svc = PedidoService(db)
    # Verifica se o pedido pertence ao cliente
    pedido = svc.repo.get_pedido(pedido_id)
    if not pedido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

    return svc.atualizar_itens_pedido(pedido_id, itens)


# ======================================================================
# ================= VINCULAR/DESVINCULAR ENTREGADOR ====================
@router.put(
    "/{pedido_id}/entregador",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def vincular_entregador(
    pedido_id: int = Path(..., description="ID do pedido"),
    payload: VincularEntregadorRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Vincula ou desvincula um entregador a um pedido.
    - Para vincular: envie entregador_id com o ID do entregador
    - Para desvincular: envie entregador_id como null
    """
    logger.info(f"[Pedidos] Vincular entregador - pedido_id={pedido_id} -> entregador_id={payload.entregador_id}")
    svc = PedidoService(db)
    return svc.vincular_entregador(pedido_id, payload.entregador_id)


# ======================================================================
# ==================== PEDIDOS PENDENTES DE IMPRESSÃO ==================
@router.get(
    "/impressao/pendentes",
    response_model=list[PedidoKanbanResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def listar_pedidos_pendentes_impressao(
    empresa_id: int = Query(..., description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os pedidos com status 'I' (Pendente de Impressão).
    """
    logger.info(f"[Pedidos] Listar pendentes de impressão - empresa_id={empresa_id}")
    svc = PedidoService(db)
    return svc.listar_pedidos_pendentes_impressao(empresa_id=empresa_id)


# ======================================================================
# ==================== MARCAR PEDIDO COMO IMPRESSO =====================
@router.put(
    "/{pedido_id}/marcar-impresso",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def marcar_pedido_impresso(
    pedido_id: int = Path(..., description="ID do pedido"),
    db: Session = Depends(get_db),
):
    """
    Marca um pedido como impresso, mudando o status de 'I' (Pendente de Impressão) 
    para 'R' (Em Preparo).
    """
    logger.info(f"[Pedidos] Marcar como impresso - pedido_id={pedido_id}")
    svc = PedidoService(db)
    return svc.marcar_pedido_impresso(pedido_id)


# ======================================================================
# ==================== IMPRIMIR PEDIDO VIA PRINTER API ================
@router.post(
    "/{pedido_id}/imprimir",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
async def imprimir_pedido_via_printer(
    pedido_id: int = Path(..., description="ID do pedido"),
    db: Session = Depends(get_db),
):
    """
    Imprime um pedido específico via Printer API.
    """
    from app.api.delivery.services.printer_integration_service import PrinterIntegrationService
    
    logger.info(f"[Pedidos] Imprimir via Printer API - pedido_id={pedido_id}")
    printer_service = PrinterIntegrationService(db)
    return await printer_service.imprimir_pedido(pedido_id)


# ======================================================================
# ==================== IMPRIMIR TODOS OS PENDENTES ====================
@router.post(
    "/impressao/imprimir-todos",
    status_code=status.HTTP_200_OK,
)
async def imprimir_todos_pendentes(
    empresa_id: int = Query(..., description="ID da empresa"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de pedidos para imprimir"),
    db: Session = Depends(get_db),
):
    """
    Imprime todos os pedidos pendentes de impressão de uma empresa via Printer API.
    """
    from app.api.delivery.services.printer_integration_service import PrinterIntegrationService
    
    logger.info(f"[Pedidos] Imprimir todos pendentes - empresa_id={empresa_id}, limite={limite}")
    printer_service = PrinterIntegrationService(db)
    return await printer_service.imprimir_pedidos_pendentes(empresa_id, limite)


# ======================================================================
# ==================== VERIFICAR CONECTIVIDADE PRINTER ================
@router.get(
    "/impressao/status-printer",
    status_code=status.HTTP_200_OK,
)
async def verificar_status_printer(
    db: Session = Depends(get_db),
):
    """
    Verifica se a Printer API está funcionando.
    """
    from app.api.delivery.services.printer_integration_service import PrinterIntegrationService
    
    logger.info("[Pedidos] Verificar status da Printer API")
    printer_service = PrinterIntegrationService(db)
    conectado = await printer_service.verificar_conectividade()
    
    return {
        "conectado": conectado,
        "mensagem": "Printer API funcionando" if conectado else "Printer API não acessível"
    }
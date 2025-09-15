"""
Router para operações relacionadas à Printer API
"""
from typing import List, Optional
from fastapi import APIRouter, status, Path, Query, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.api.delivery.services.printer_service import PrinterService
from app.api.delivery.schemas.schema_printer import (
    RespostaImpressaoPrinter,
    RespostaImpressaoMultipla,
    StatusPrinterResponse,
    ConfigImpressaoPrinter,
    ImpressaoMultiplaRequest,
    PedidoPendenteImpressaoResponse
)
from app.core.admin_dependencies import get_current_user
from app.api.mensura.models.user_model import UserModel
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/printer", tags=["Printer"])


# ======================================================================
# ==================== VERIFICAR STATUS PRINTER =======================
@router.get(
    "/status",
    response_model=StatusPrinterResponse,
    status_code=status.HTTP_200_OK,
)
async def verificar_status_printer(
    db: Session = Depends(get_db),
):
    """
    Verifica se a Printer API está funcionando.
    """
    logger.info("[Printer] Verificar status da Printer API")
    printer_service = PrinterService(db)
    return await printer_service.verificar_status_printer()


# ======================================================================
# ==================== BUSCAR PEDIDOS PENDENTES =======================
@router.get(
    "/imprimir-pendentes",
    response_model=List[PedidoPendenteImpressaoResponse],
    status_code=status.HTTP_200_OK,
)
async def buscar_pedidos_pendentes_impressao(
    empresa_id: int = Query(..., description="ID da empresa"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de pedidos para buscar"),
    db: Session = Depends(get_db),
):
    """
    Busca pedidos pendentes de impressão formatados para o endpoint GET.
    Retorna os dados no formato específico solicitado.
    """
    logger.info(f"[Printer] Buscar pedidos pendentes - empresa_id={empresa_id}, limite={limite}")
    printer_service = PrinterService(db)
    return printer_service.get_pedidos_pendentes_para_impressao(empresa_id, limite)




# ======================================================================
# ==================== IMPRIMIR TODOS OS PENDENTES ====================
@router.post(
    "/imprimir-pendentes",
    response_model=RespostaImpressaoMultipla,
    status_code=status.HTTP_200_OK,
)
async def imprimir_pedidos_pendentes(
    empresa_id: int = Query(..., description="ID da empresa"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de pedidos para imprimir"),
    config: Optional[ConfigImpressaoPrinter] = Body(None, description="Configurações de impressão"),
    db: Session = Depends(get_db),
):
    """
    Imprime todos os pedidos pendentes de impressão de uma empresa via Printer API.
    """
    logger.info(f"[Printer] Imprimir pendentes - empresa_id={empresa_id}, limite={limite}")
    printer_service = PrinterService(db)
    return await printer_service.imprimir_pedidos_pendentes(empresa_id, limite, config)


# ======================================================================
# ==================== LISTAR PEDIDOS PENDENTES =======================
@router.get(
    "/pedidos-pendentes",
    response_model=List[PedidoPendenteImpressaoResponse],
    status_code=status.HTTP_200_OK,
)
async def listar_pedidos_pendentes_impressao(
    empresa_id: int = Query(..., description="ID da empresa"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de pedidos para listar"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os pedidos pendentes de impressão de uma empresa.
    """
    logger.info(f"[Printer] Listar pendentes - empresa_id={empresa_id}, limite={limite}")
    printer_service = PrinterService(db)
    return printer_service.get_pedidos_pendentes_para_impressao(empresa_id, limite)


# ======================================================================
# ==================== MARCAR PEDIDO COMO IMPRESSO ====================
@router.put(
    "/marcar-impresso/{pedido_id}",
    response_model=RespostaImpressaoPrinter,
    status_code=status.HTTP_200_OK,
)
async def marcar_pedido_impresso_manual(
    pedido_id: int = Path(..., description="ID do pedido"),
    db: Session = Depends(get_db),
):
    """
    Marca um pedido como impresso manualmente (sem usar Printer API).
    Útil quando a impressão é feita externamente.
    """
    logger.info(f"[Printer] Marcar como impresso manualmente - pedido_id={pedido_id}")
    printer_service = PrinterService(db)
    return printer_service.marcar_pedido_impresso_manual(pedido_id)


# ======================================================================
# ==================== ESTATÍSTICAS DE IMPRESSÃO ======================
@router.get(
    "/estatisticas",
    status_code=status.HTTP_200_OK,
)
async def get_estatisticas_impressao(
    empresa_id: int = Query(..., description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """
    Retorna estatísticas de impressão para uma empresa.
    """
    logger.info(f"[Printer] Estatísticas - empresa_id={empresa_id}")
    printer_service = PrinterService(db)
    return printer_service.get_estatisticas_impressao(empresa_id)


# ======================================================================
# ==================== IMPRIMIR MÚLTIPLOS PEDIDOS =====================
@router.post(
    "/imprimir-multiplos",
    response_model=RespostaImpressaoMultipla,
    status_code=status.HTTP_200_OK,
)
async def imprimir_multiplos_pedidos(
    request: ImpressaoMultiplaRequest,
    db: Session = Depends(get_db),
):
    """
    Imprime múltiplos pedidos com configurações personalizadas.
    """
    logger.info(f"[Printer] Imprimir múltiplos - empresa_id={request.empresa_id}, limite={request.limite}")
    printer_service = PrinterService(db)
    return await printer_service.imprimir_pedidos_pendentes(
        request.empresa_id, 
        request.limite, 
        request.config
    )





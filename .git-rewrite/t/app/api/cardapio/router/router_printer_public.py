"""
Router para operações relacionadas à Printer API
"""
from fastapi import APIRouter, status, Path, Query, Depends
from sqlalchemy.orm import Session

from app.api.cardapio.services.service_printer import PrinterService
from app.api.cardapio.schemas.schema_printer import (
    PedidosPendentesPrinterResponse,
    RespostaImpressaoPrinter,
    TipoPedidoPrinterEnum,
)
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/cardapio/printer", tags=["Public - Cardápio - Printer"])


# ======================================================================
# ==================== LISTAR PEDIDOS PENDENTES =======================
@router.get(
    "/pedidos-pendentes",
    response_model=PedidosPendentesPrinterResponse,
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
    tipo_pedido: TipoPedidoPrinterEnum = Query(..., description="Canal do pedido: delivery, mesa ou balcao"),
    db: Session = Depends(get_db),
):
    """
    Marca um pedido como impresso manualmente (sem usar Printer API).
    Útil quando a impressão é feita externamente.
    """
    logger.info(f"[Printer] Marcar como impresso manualmente - pedido_id={pedido_id}")
    printer_service = PrinterService(db)
    return printer_service.marcar_pedido_impresso_manual(pedido_id, tipo_pedido)


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



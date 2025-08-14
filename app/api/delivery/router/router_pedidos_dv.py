#
from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.orm import Session

from app.api.delivery.schemas.schema_pedido_dv import FinalizarPedidoRequest, PedidoResponse
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum
from app.api.delivery.services.pedido_service import PedidoService
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos", tags=["Pedidos"])

@router.post("/checkout", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def checkout(payload: FinalizarPedidoRequest, db: Session = Depends(get_db)):
    logger.info("[Pedidos] Checkout iniciado")
    svc = PedidoService(db)
    return svc.finalizar_pedido(payload)

@router.post("/{pedido_id}/confirmar-pagamento", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def confirmar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
    gateway: PagamentoGatewayEnum = PagamentoGatewayEnum.PIX_INTERNO,
    db: Session = Depends(get_db),
):
    logger.info(f"[Pedidos] Confirmar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}")
    svc = PedidoService(db)
    return await svc.confirmar_pagamento(pedido_id=pedido_id, metodo=metodo, gateway=gateway)

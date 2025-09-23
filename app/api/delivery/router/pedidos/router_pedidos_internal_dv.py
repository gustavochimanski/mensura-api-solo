from typing import List, Literal

from fastapi import APIRouter, status, Path, Query, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido import FinalizarPedidoRequest, PedidoResponse, PedidoResponseCompleto, EditarPedidoRequest, ItemPedidoEditar, PedidoResponseSimplificado, ModoEdicaoRequest
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum
from app.api.delivery.services.pedidos.service_pedido import PedidoService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

# Router interno - não incluído na geração do cliente
router = APIRouter(prefix="/api/delivery/cliente/pedidos", tags=["Pedidos - Cliente - Delivery - Internal"])

# ======================================================================
# ==================== CONFIRMAR PAGAMENTO =============================
@router.post("/{pedido_id}/confirmar-pagamento", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def confirmar_pagamento(
    pedido_id: int = Path(..., description="ID do pedido"),
    metodo: PagamentoMetodoEnum = Query(default="PIX", description="Método de pagamento"),
    gateway: PagamentoGatewayEnum = Query(default="PIX_INTERNO", description="Gateway de pagamento"),
    db: Session = Depends(get_db),
):
    logger.info(f"[Pedidos] Confirmar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}")
    svc = PedidoService(db)
    return await svc.confirmar_pagamento(pedido_id=pedido_id, metodo=metodo, gateway=gateway)

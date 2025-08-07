# app/api/pedidos/controller.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.delivery.schemas.pedidos_schema import PedidoResponse, FinalizarPedidoRequest
from app.api.delivery.services.pedidos_service import PedidoService
from app.database.db_connection import get_db

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.post(
    "/finalizar",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Finalizar Pedido"
)
def finalizar_pedido_endpoint(
    payload: FinalizarPedidoRequest,
    db: Session = Depends(get_db),
):
    service = PedidoService(db)
    return service.finalizar_pedido(payload)

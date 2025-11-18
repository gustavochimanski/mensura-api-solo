from fastapi import APIRouter, Depends, Path, status, Body
from sqlalchemy.orm import Session

from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.mesas.schemas.schema_pedido_mesa import (
    PedidoMesaOut,
    FecharContaMesaRequest,
)
from app.api.mesas.services.service_pedidos_mesa import PedidoMesaService
from app.api.mesas.services.dependencies import get_pedido_mesa_service
from app.api.cadastros.models.model_cliente_dv import ClienteModel


router = APIRouter(
    prefix="/api/mesas/client/pedidos",
    tags=["Client - Mesas - Pedidos"],
)


@router.post("/{pedido_id}/fechar-conta", response_model=PedidoMesaOut, status_code=status.HTTP_200_OK)
def fechar_conta_pedido_cliente(
    pedido_id: int = Path(...),
    payload: FecharContaMesaRequest = Body(...),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
    svc: PedidoMesaService = Depends(get_pedido_mesa_service),
):
    return svc.fechar_conta_cliente(pedido_id, cliente.id, payload)



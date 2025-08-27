from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.delivery.schemas.schema_cliente import ClienteOut, ClienteUpdate, ClienteCreate
from app.api.delivery.services.service_cliente import ClienteService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente", tags=["Cliente"])

@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_new_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    logger.info("[Cliente] Create")
    cliente = ClienteService(db).create(data)
    return {
        "telefone": cliente.telefone,
        "nome": cliente.nome,
        "super_token": cliente.super_token
    }

@router.get("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def read_current_cliente(
    cliente: "ClienteDeliveryModel" = Depends(get_cliente_by_super_token)
):
    logger.info(f"[Cliente] Get current {cliente.telefone}")
    return cliente

@router.put("/me", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def update_current_cliente(
    data: ClienteUpdate,
    cliente: "ClienteDeliveryModel" = Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Cliente] Update {cliente.telefone}")
    service = ClienteService(db)
    return service.update(cliente.super_token, data)

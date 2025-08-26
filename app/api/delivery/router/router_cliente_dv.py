from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.delivery.schemas.schema_cliente import ClienteOut, ClienteUpdate, ClienteCreate
from app.api.delivery.services.service_cliente import ClienteService
from app.core.dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente", tags=["Cliente"])

@router.get("/", response_model=ClienteOut, status_code=status.HTTP_200_OK, dependencies=[Depends(get_current_user)])
def read_current_cliente(db: Session = Depends(get_db)):
    logger.info("[Cliente] Get current")
    cliente = ClienteService(db).get_current()
    return cliente

@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_new_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db)
):
    logger.info("[Cliente] Create")
    cliente =ClienteService(db).create(data)
    return cliente

@router.put("/{cliente_id}", response_model=ClienteOut, status_code=status.HTTP_200_OK, dependencies=[Depends(get_current_user)])
def update_existing_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db)
):
    logger.info(f"[Cliente] Update ID={cliente_id}")
    updated = ClienteService(db).update(cliente_id, data)
    return updated

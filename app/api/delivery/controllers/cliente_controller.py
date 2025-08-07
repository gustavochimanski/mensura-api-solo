# src/app/api/delivery/routers/cliente_router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.delivery.schemas.cliente_schema import ClienteOut, ClienteUpdate, ClienteCreate
from app.api.delivery.services.cliente_service import (
    get_current_cliente,
    create_cliente,
    update_cliente,
)
from app.database.db_connection import get_db  # sua dependência padrão

router = APIRouter(prefix="/cliente", tags=["Cliente"])

@router.get("/", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def read_current_cliente(db: Session = Depends(get_db)):
    """
    Busca o cliente "logado" (ou único).
    """
    cliente = get_current_cliente(db)
    return cliente

@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_new_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo cliente.
    """
    cliente = create_cliente(db, data)
    return cliente

@router.put("/{cliente_id}", response_model=ClienteOut, status_code=status.HTTP_200_OK)
def update_existing_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza dados de um cliente existente.
    """
    updated = update_cliente(db, cliente_id, data)
    return updated

# src/app/api/delivery/services/cliente_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.repositories.cliente_repo import ClienteRepository
from app.api.delivery.schemas.cliente_schema import ClienteUpdate, ClienteCreate


def get_current_cliente(db: Session):
    repo = ClienteRepository(db)
    cliente = repo.get_current()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return cliente

def create_cliente(db: Session, data: ClienteCreate):
    repo = ClienteRepository(db)
    return repo.create(data)

def update_cliente(db: Session, cliente_id: int, data: ClienteUpdate):
    repo = ClienteRepository(db)
    db_obj = repo.get_by_id(cliente_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não existe")
    return repo.update(db_obj, data)

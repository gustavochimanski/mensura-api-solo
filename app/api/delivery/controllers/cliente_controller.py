# app/api/mensura/controllers/cliente_controller.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.api.delivery.schemas.cliente_schema import ClienteResponse, ClienteCreate, ClienteUpdate
from app.api.delivery.services.cliente_service import ClienteService
from app.database.db_connection import get_db

router = APIRouter(prefix="/clientes", tags=["Clientes"])

@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_cliente(request: ClienteCreate, db: Session = Depends(get_db)):
    return ClienteService(db).create_cliente(request)

@router.get("/{id}", response_model=ClienteResponse)
def get_cliente(id: int, db: Session = Depends(get_db)):
    return ClienteService(db).get_cliente(id)

@router.get("/", response_model=List[ClienteResponse])
def list_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return ClienteService(db).list_clientes(skip, limit)

@router.put("/{id}", response_model=ClienteResponse)
def update_cliente(id: int, request: ClienteUpdate, db: Session = Depends(get_db)):
    return ClienteService(db).update_cliente(id, request)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(id: int, db: Session = Depends(get_db)):
    ClienteService(db).delete_cliente(id)

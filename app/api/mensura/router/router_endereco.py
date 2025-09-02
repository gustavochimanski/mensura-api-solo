# app/api/mensura/router/router_endereco.py
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.mensura.services.endereco_service import EnderecoService
from app.api.mensura.schemas.schema_endereco import EnderecoCreate, EnderecoUpdate, EnderecoResponse

router = APIRouter(prefix="/api/mensura/enderecos", tags=["Enderecos"])

@router.post("/", response_model=EnderecoResponse)
def create_endereco(request: EnderecoCreate, db: Session = Depends(get_db)):
    return EnderecoService(db).create_endereco(request)

@router.get("/{id}", response_model=EnderecoResponse)
def get_endereco(id: int, db: Session = Depends(get_db)):
    return EnderecoService(db).get_endereco(id)

@router.get("/", response_model=List[EnderecoResponse])
def list_enderecos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return EnderecoService(db).list_enderecos(skip, limit)

@router.put("/{id}", response_model=EnderecoResponse)
def update_endereco(id: int, request: EnderecoUpdate, db: Session = Depends(get_db)):
    return EnderecoService(db).update_endereco(id, request)

@router.delete("/{id}", status_code=204)
def delete_endereco(id: int, db: Session = Depends(get_db)):
    EnderecoService(db).delete_endereco(id)

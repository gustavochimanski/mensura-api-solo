# app/api/mensura/router/empresa_controller.py
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.mensura.services.empresa_service import EmpresaService
from app.api.mensura.schemas.empresa_schema import EmpresaCreate, EmpresaUpdate, EmpresaResponse

router = APIRouter(prefix="/empresas", tags=["Empresas"])

@router.post("/", response_model=EmpresaResponse)
def create_empresa(request: EmpresaCreate, db: Session = Depends(get_db)):
    return EmpresaService(db).create_empresa(request)

@router.get("/{id}", response_model=EmpresaResponse)
def get_empresa(id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).get_empresa(id)

@router.get("/", response_model=List[EmpresaResponse])
def list_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return EmpresaService(db).list_empresas(skip, limit)

@router.put("/{id}", response_model=EmpresaResponse)
def update_empresa(id: int, request: EmpresaUpdate, db: Session = Depends(get_db)):
    return EmpresaService(db).update_empresa(id, request)

@router.delete("/{id}", status_code=204)
def delete_empresa(id: int, db: Session = Depends(get_db)):
    EmpresaService(db).delete_empresa(id)

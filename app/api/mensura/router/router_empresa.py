from typing import List
from fastapi import APIRouter, Depends, UploadFile, Form
from sqlalchemy.orm import Session
import json

from app.database.db_connection import get_db
from app.api.mensura.services.empresa_service import EmpresaService
from app.api.mensura.schemas.empresa_schema import EmpresaResponse
from app.api.mensura.schemas.endereco_schema import EnderecoCreate

router = APIRouter(prefix="/api/mensura/empresas", tags=["Empresas"])

@router.post("/", response_model=EmpresaResponse)
async def create_empresa(
    nome: str = Form(...),
    cnpj: str | None = Form(None),
    slug: str = Form(...),
    endereco: str = Form(...),  # JSON string
    logo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    endereco_data = EnderecoCreate(**json.loads(endereco))
    return EmpresaService(db).create_empresa(
        nome=nome, cnpj=cnpj, slug=slug, endereco=endereco_data, logo=logo
    )

@router.put("/{id}", response_model=EmpresaResponse)
async def update_empresa(
    id: int,
    nome: str = Form(None),
    cnpj: str | None = Form(None),
    slug: str = Form(None),
    endereco_id: int | None = Form(None),
    logo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    return EmpresaService(db).update_empresa(
        id=id, nome=nome, cnpj=cnpj, slug=slug, endereco_id=endereco_id, logo=logo
    )

@router.get("/{id}", response_model=EmpresaResponse)
def get_empresa(id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).get_empresa(id)

@router.get("/", response_model=List[EmpresaResponse])
def list_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return EmpresaService(db).list_empresas(skip, limit)

@router.delete("/{id}", status_code=204)
def delete_empresa(id: int, db: Session = Depends(get_db)):
    EmpresaService(db).delete_empresa(id)

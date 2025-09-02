from typing import List
from fastapi import APIRouter, Depends, UploadFile, Form
from sqlalchemy.orm import Session
import json

from app.database.db_connection import get_db
from app.api.mensura.services.empresa_service import EmpresaService
from app.api.mensura.schemas.schema_empresa import EmpresaResponse, EmpresaUpdate
from app.api.mensura.schemas.schema_empresa import EmpresaCreate
from app.api.mensura.schemas.schema_endereco import EnderecoCreate

router = APIRouter(prefix="/api/mensura/empresas", tags=["Empresas"])


@router.post("/", response_model=EmpresaResponse)
async def create_empresa(
    nome: str = Form(...),
    cnpj: str | None = Form(None),
    slug: str = Form(...),
    endereco: str = Form(...),
    logo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    endereco_data = EnderecoCreate(**json.loads(endereco))
    empresa_data = EmpresaCreate(
        nome=nome,
        cnpj=cnpj,
        slug=slug,
        endereco=endereco_data,
        logo=None  # ⚠️ não passa o UploadFile aqui
    )
    empresa = EmpresaService(db).create_empresa(empresa_data, logo)  # envia logo separado
    return empresa


@router.put("/{id}", response_model=EmpresaResponse)
async def update_empresa(
    id: int,
    nome: str = Form(None),
    cnpj: str | None = Form(None),
    slug: str = Form(None),
    endereco_id: int | None = Form(None),
    cardapio_link: str | None = Form(None),
    cardapio_tema: str | None = Form(None),
    logo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    empresa_data = EmpresaUpdate(
        nome=nome,
        cnpj=cnpj,
        slug=slug,
        endereco_id=endereco_id,
        cardapio_link=cardapio_link,
        cardapio_tema=cardapio_tema,
    )

    # Passa logo separadamente
    return EmpresaService(db).update_empresa(id=id, data=empresa_data, logo=logo)



@router.get("/{id}", response_model=EmpresaResponse)
def get_empresa(id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).get_empresa(id)

@router.get("/", response_model=List[EmpresaResponse])
def list_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return EmpresaService(db).list_empresas(skip, limit)

@router.delete("/{id}", status_code=204)
def delete_empresa(id: int, db: Session = Depends(get_db)):
    EmpresaService(db).delete_empresa(id)

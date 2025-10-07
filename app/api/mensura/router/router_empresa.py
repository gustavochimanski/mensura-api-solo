# app/api/mensura/routes/empresa_router.py
from fastapi import APIRouter, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List
import json

from app.database.db_connection import get_db
from app.api.mensura.schemas.schema_empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaResponse,
    EmpresaCardapioLinkResponse,
)
from app.api.mensura.schemas.schema_endereco import EnderecoCreate
from app.api.mensura.services.empresa_service import EmpresaService
from app.utils.slug_utils import make_slug

router = APIRouter(prefix="/api/mensura/empresas", tags=["Empresas"])

@router.get("/cardapios", response_model=List[EmpresaCardapioLinkResponse])
def list_cardapio_links(db: Session = Depends(get_db)):
    return EmpresaService(db).list_cardapio_links()


# Criar empresa
@router.post("/", response_model=EmpresaResponse)
async def create_empresa(
    nome: str = Form(...),
    cnpj: str | None = Form(None),
    endereco: str = Form(...),  # JSON string
    logo: UploadFile | None = None,
    cardapio_link: str | None = Form(None),
    cardapio_tema: str | None = Form("padrao"),
    aceita_pedido_automatico: str | None = Form("false"),
    tempo_entrega_maximo: int = Form(...),
    db: Session = Depends(get_db),
):
    endereco_data = EnderecoCreate(**json.loads(endereco))
    slug = make_slug(nome)
    empresa_data = EmpresaCreate(
        nome=nome,
        cnpj=cnpj,
        slug=slug,
        endereco=endereco_data,
        cardapio_link=cardapio_link,
        cardapio_tema=cardapio_tema,
        aceita_pedido_automatico = aceita_pedido_automatico.lower() == "true",
        tempo_entrega_maximo=tempo_entrega_maximo,
    )
    return EmpresaService(db).create_empresa(empresa_data, logo=logo)

# Atualizar empresa
@router.put("/{id}", response_model=EmpresaResponse)
async def update_empresa(
    id: int,
    nome: str | None = Form(None),
    cnpj: str | None = Form(None),
    endereco_id: int | None = Form(None),
    endereco: str | None = Form(None),  # JSON string
    logo: UploadFile | None = None,
    cardapio_link: str | None = Form(None),
    cardapio_tema: str | None = Form(None),
    aceita_pedido_automatico: str | None = Form(None),
    tempo_entrega_maximo: int | None = Form(None),
    db: Session = Depends(get_db),
):
    slug = make_slug(nome) if nome else None
    empresa_data = EmpresaUpdate(
        nome=nome,
        cnpj=cnpj,
        slug=slug,
        endereco_id=endereco_id,
        cardapio_link=cardapio_link,
        cardapio_tema=cardapio_tema,
        aceita_pedido_automatico = aceita_pedido_automatico.lower() == "true" if aceita_pedido_automatico else None,
        tempo_entrega_maximo=tempo_entrega_maximo,
        endereco=EnderecoCreate(**json.loads(endereco)) if endereco else None
    )
    return EmpresaService(db).update_empresa(id=id, data=empresa_data, logo=logo)



# Pegar uma empresa pelo id
@router.get("/{id}", response_model=EmpresaResponse)
def get_empresa(id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).get_empresa(id)


# Listar empresas
@router.get("/", response_model=List[EmpresaResponse])
def list_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return EmpresaService(db).list_empresas(skip, limit)


# Deletar empresa
@router.delete("/{id}", status_code=204)
def delete_empresa(id: int, db: Session = Depends(get_db)):
    EmpresaService(db).delete_empresa(id)

# app/api/mensura/routes/empresa_router.py
from fastapi import APIRouter, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List
import json

from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.mensura.schemas.schema_empresa import EmpresaCreate, EmpresaUpdate, EmpresaResponse
from app.api.mensura.schemas.schema_endereco import EnderecoCreate
from app.api.mensura.services.empresa_service import EmpresaService
from app.utils.slug_utils import make_slug

router = APIRouter(prefix="/api/mensura/empresas", tags=["Empresas Client"])
@router.get("/client", )
def buscar_empresa_client(
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    repo_emp = EmpresaRepository(db)
    empresas = repo_emp.list()

    return empresas
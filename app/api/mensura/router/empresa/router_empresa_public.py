# app/api/mensura/routes/empresa_router.py
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.schema_empresa_client import EmpresaClientOut
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db


router = APIRouter(prefix="/api/mensura/public/emp", tags=["Public - Mensura - Empresas"])
@router.get("/", response_model=EmpresaClientOut)
def buscar_empresa_client(
    empresa_id: int,
    db: Session = Depends(get_db)
):
    repo_emp = EmpresaRepository(db)
    return repo_emp.get_empresa_by_id(empresa_id)
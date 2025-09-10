# app/api/mensura/routes/empresa_router.py
from fastapi import APIRouter, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List
import json

from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db


router = APIRouter(prefix="/api/mensura/empresas", tags=["Empresas Client"])
@router.get("/client", dependencies=[Depends(get_cliente_by_super_token)] )
def buscar_empresa_client(
    db: Session = Depends(get_db)
):
    repo_emp = EmpresaRepository(db)
    empresas = repo_emp.list()

    return empresas
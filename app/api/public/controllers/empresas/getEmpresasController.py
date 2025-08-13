# app/api/public/router/empresas.py
import logging
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from app.database.db_connection import get_db
from app.api.public.repositories.empresas.consultaEmpresas import EmpresasRepository

router = APIRouter(prefix="api/public/empresas", tags=["Public"])
logger = logging.getLogger(__name__)

@router.get("", summary="Buscar códigos das empresas ativas")
def get_empresas_codigos(db: Session = Depends(get_db)):
    repo = EmpresasRepository(db)
    return repo.buscar_codigos_ativos()

@router.get("/detalhes", summary="Buscar objetos completos das empresas ativas")
def get_empresas_completas(db: Session = Depends(get_db)):
    repo = EmpresasRepository(db)
    return repo.buscar_empresas_ativas()

# app/api/empresas/router/public/router_empresa_public.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.empresas.schemas.schema_empresa_client import (
    EmpresaClientOut,
    EmpresaPublicListItem,
)
from app.database.db_connection import get_db


router = APIRouter(prefix="/api/empresas/public/emp", tags=["Public - Empresas"])


@router.get(
    "/lista",
    response_model=list[EmpresaPublicListItem],
    summary="Listar empresas públicas",
    description="Retorna empresas disponíveis para seleção pública, com filtros opcionais.",
)
def listar_empresas_publicas(
    empresa_id: int | None = Query(None, description="Filtrar por ID da empresa"),
    q: str | None = Query(None, description="Termo de busca por nome ou slug"),
    cidade: str | None = Query(None, description="Filtrar por cidade"),
    estado: str | None = Query(None, description="Filtrar por estado (sigla)"),
    limit: int = Query(100, ge=1, le=500, description="Limite máximo de empresas retornadas"),
    db: Session = Depends(get_db),
):
    repo_emp = EmpresaRepository(db)
    empresas = repo_emp.search_public(
        empresa_id=empresa_id,
        q=q,
        cidade=cidade,
        estado=estado,
        limit=limit,
    )
    if empresa_id is not None and not empresas:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return [
        EmpresaPublicListItem(
            id=empresa.id,
            nome=empresa.nome,
            logo=empresa.logo,
            bairro=empresa.bairro,
            cidade=empresa.cidade,
            estado=empresa.estado,
            distancia_km=None,
            tema=empresa.cardapio_tema,
            redireciona_home=empresa.redireciona_home,
            redireciona_home_para=empresa.redireciona_home_para,
        )
        for empresa in empresas
    ]


@router.get("/", response_model=EmpresaClientOut)
def buscar_empresa_client(
    empresa_id: int = Query(..., description="ID da empresa"),
    db: Session = Depends(get_db)
):
    repo_emp = EmpresaRepository(db)
    return repo_emp.get_empresa_by_id(empresa_id)


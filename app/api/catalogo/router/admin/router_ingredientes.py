from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_ingrediente import (
    IngredienteResponse,
    CriarIngredienteRequest,
    AtualizarIngredienteRequest,
)
from app.api.catalogo.services.service_ingrediente import IngredienteService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/ingredientes",
    tags=["Admin - Catalogo - Receitas - Ingredientes"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=List[IngredienteResponse])
def listar_ingredientes(
    empresa_id: int = Query(..., description="ID da empresa"),
    apenas_ativos: bool = Query(True, description="Apenas ingredientes ativos"),
    search: Optional[str] = Query(None, description="Termo de busca (nome ou descrição)"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os ingredientes de uma empresa.

    - Se `search` for informado, filtra por nome/descrição contendo o termo (case-insensitive).
    - Caso contrário, retorna a listagem completa (respeitando `apenas_ativos`).
    """
    logger.info(f"[Ingredientes] Listar - empresa={empresa_id} apenas_ativos={apenas_ativos} search={search!r}")
    service = IngredienteService(db)
    return service.listar_ingredientes(empresa_id, apenas_ativos, search=search)


@router.post("/", response_model=IngredienteResponse, status_code=status.HTTP_201_CREATED)
def criar_ingrediente(
    req: CriarIngredienteRequest,
    db: Session = Depends(get_db),
):
    """Cria um novo ingrediente."""
    logger.info(f"[Ingredientes] Criar - empresa={req.empresa_id} nome={req.nome} custo={req.custo}")
    service = IngredienteService(db)
    return service.criar_ingrediente(req)


@router.get("/{ingrediente_id}", response_model=IngredienteResponse)
def buscar_ingrediente(
    ingrediente_id: int,
    db: Session = Depends(get_db),
):
    """Busca um ingrediente por ID."""
    logger.info(f"[Ingredientes] Buscar - id={ingrediente_id}")
    service = IngredienteService(db)
    return service.buscar_por_id(ingrediente_id)


@router.put("/{ingrediente_id}", response_model=IngredienteResponse)
def atualizar_ingrediente(
    ingrediente_id: int,
    req: AtualizarIngredienteRequest,
    db: Session = Depends(get_db),
):
    """Atualiza um ingrediente existente."""
    logger.info(f"[Ingredientes] Atualizar - id={ingrediente_id}")
    service = IngredienteService(db)
    return service.atualizar_ingrediente(ingrediente_id, req)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_200_OK)
def deletar_ingrediente(
    ingrediente_id: int,
    db: Session = Depends(get_db),
):
    """Deleta um ingrediente. Só é possível deletar se o ingrediente não estiver vinculado a nenhuma receita."""
    logger.info(f"[Ingredientes] Deletar - id={ingrediente_id}")
    service = IngredienteService(db)
    return service.deletar_ingrediente(ingrediente_id)


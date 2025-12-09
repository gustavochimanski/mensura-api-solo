from typing import List
from fastapi import APIRouter, Depends, status, Path, Query
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_complemento import (
    AdicionalResponse,
    CriarItemRequest,
    AtualizarAdicionalRequest,
)
from app.api.catalogo.services.service_complemento import ComplementoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/catalogo/admin/adicionais",
    tags=["Admin - Catalogo - Adicionais"],
    dependencies=[Depends(get_current_user)]
)


# ------ CRUD de Adicionais (Independentes) ------
@router.post("/", response_model=AdicionalResponse, status_code=status.HTTP_201_CREATED)
def criar_adicional(
    req: CriarItemRequest,
    db: Session = Depends(get_db),
):
    """Cria um adicional independente (pode ser usado em complementos, receitas, combos, etc.)."""
    logger.info(f"[Adicionais] Criar - empresa={req.empresa_id} nome={req.nome}")
    service = ComplementoService(db)
    return service.criar_item(req)


@router.get("/", response_model=List[AdicionalResponse])
def listar_adicionais(
    empresa_id: int = Query(..., description="ID da empresa"),
    apenas_ativos: bool = Query(True, description="Apenas adicionais ativos"),
    termo: str = Query(None, description="Termo de busca (nome ou descrição)"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os adicionais de uma empresa.
    
    Se 'termo' for fornecido, busca adicionais cujo nome ou descrição contenham o termo.
    """
    if termo:
        logger.info(f"[Adicionais] Buscar - empresa={empresa_id} termo={termo} apenas_ativos={apenas_ativos}")
        service = ComplementoService(db)
        return service.buscar_adicionais(empresa_id, termo, apenas_ativos)
    else:
        logger.info(f"[Adicionais] Listar - empresa={empresa_id} apenas_ativos={apenas_ativos}")
        service = ComplementoService(db)
        return service.listar_itens(empresa_id, apenas_ativos)


@router.get("/{adicional_id}", response_model=AdicionalResponse)
def buscar_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """Busca um adicional por ID."""
    logger.info(f"[Adicionais] Buscar - id={adicional_id}")
    service = ComplementoService(db)
    return service.buscar_item_por_id(adicional_id)


@router.put("/{adicional_id}", response_model=AdicionalResponse)
def atualizar_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    req: AtualizarAdicionalRequest = Depends(),
    db: Session = Depends(get_db),
):
    """Atualiza um adicional existente."""
    logger.info(f"[Adicionais] Atualizar - id={adicional_id}")
    service = ComplementoService(db)
    return service.atualizar_item(adicional_id, req)


@router.delete("/{adicional_id}", status_code=status.HTTP_200_OK)
def deletar_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """Deleta um adicional (remove automaticamente os vínculos com complementos, receitas, etc.)."""
    logger.info(f"[Adicionais] Deletar - id={adicional_id}")
    service = ComplementoService(db)
    service.deletar_item(adicional_id)
    return {"message": "Adicional deletado com sucesso"}


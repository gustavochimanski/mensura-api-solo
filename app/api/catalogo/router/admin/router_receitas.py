from fastapi import APIRouter, Depends, Body, Path, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.catalogo.services.service_receitas import ReceitasService
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIn,
    ReceitaOut,
    ReceitaUpdate,
    ReceitaIngredienteIn,
    ReceitaIngredienteOut,
    AdicionalIn,
    AdicionalOut,
)
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/catalogo/admin/receitas",
    tags=["Admin - Catalogo - Receitas"],
    dependencies=[Depends(get_current_user)]
)


# Receitas - CRUD completo
@router.post("/", response_model=ReceitaOut, status_code=status.HTTP_201_CREATED)
def create_receita(
    body: ReceitaIn,
    db: Session = Depends(get_db),
):
    """Cria uma nova receita"""
    logger.info(f"[Receitas] Criar - empresa={body.empresa_id} nome={body.nome}")
    return ReceitasService(db).create_receita(body)


@router.get("/", response_model=list[ReceitaOut])
def list_receitas(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    db: Session = Depends(get_db),
):
    """Lista todas as receitas, com filtros opcionais"""
    logger.info(f"[Receitas] Listar - empresa_id={empresa_id} ativo={ativo}")
    return ReceitasService(db).list_receitas(empresa_id=empresa_id, ativo=ativo)


@router.get("/{receita_id}", response_model=ReceitaOut)
def get_receita(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Busca uma receita por ID"""
    receita = ReceitasService(db).get_receita(receita_id)
    if not receita:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
    return receita


@router.put("/{receita_id}", response_model=ReceitaOut)
def update_receita(
    receita_id: int = Path(..., description="ID da receita"),
    body: ReceitaUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """Atualiza uma receita"""
    return ReceitasService(db).update_receita(receita_id, body)


@router.delete("/{receita_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receita(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Remove uma receita"""
    ReceitasService(db).delete_receita(receita_id)
    return None


# Ingredientes (vinculação a receitas)
@router.get("/{receita_id}/ingredientes", response_model=list[ReceitaIngredienteOut])
def list_ingredientes(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Lista todos os ingredientes de uma receita"""
    return ReceitasService(db).list_ingredientes(receita_id)


@router.post("/ingredientes", response_model=ReceitaIngredienteOut, status_code=status.HTTP_201_CREATED)
def add_ingrediente(
    body: ReceitaIngredienteIn,
    db: Session = Depends(get_db),
):
    """
    Adiciona um ingrediente a uma receita.
    
    IMPORTANTE: Um ingrediente só pode estar vinculado a UMA receita (relacionamento 1:1).
    Se o ingrediente já estiver vinculado a outra receita, retornará erro 400.
    """
    return ReceitasService(db).add_ingrediente(body)


@router.put("/ingredientes/{receita_ingrediente_id}", response_model=ReceitaIngredienteOut)
def update_ingrediente(
    receita_ingrediente_id: int = Path(..., description="ID do vínculo ingrediente-receita"),
    quantidade: Optional[float] = Body(None, description="Quantidade do ingrediente"),
    db: Session = Depends(get_db),
):
    """Atualiza a quantidade de um ingrediente em uma receita"""
    return ReceitasService(db).update_ingrediente(receita_ingrediente_id, quantidade)


@router.delete("/ingredientes/{receita_ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_ingrediente(
    receita_ingrediente_id: int = Path(..., description="ID do vínculo ingrediente-receita"),
    db: Session = Depends(get_db),
):
    """Remove um ingrediente de uma receita (desvincula, mas não deleta o ingrediente)"""
    ReceitasService(db).remove_ingrediente(receita_ingrediente_id)
    return None


# Adicionais
@router.get("/{receita_id}/adicionais", response_model=list[AdicionalOut])
def list_adicionais(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Lista todos os adicionais de uma receita"""
    return ReceitasService(db).list_adicionais(receita_id)


@router.post("/adicionais", response_model=AdicionalOut, status_code=status.HTTP_201_CREATED)
def add_adicional(
    body: AdicionalIn,
    db: Session = Depends(get_db),
):
    """Adiciona um adicional a uma receita"""
    return ReceitasService(db).add_adicional(body)


@router.put("/adicionais/{adicional_id}", response_model=AdicionalOut)
def update_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    preco: Optional[float] = Body(None, description="Preço do adicional"),
    db: Session = Depends(get_db),
):
    """Atualiza um adicional de uma receita"""
    return ReceitasService(db).update_adicional(adicional_id, preco)


@router.delete("/adicionais/{adicional_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """Remove um adicional de uma receita"""
    ReceitasService(db).remove_adicional(adicional_id)
    return None


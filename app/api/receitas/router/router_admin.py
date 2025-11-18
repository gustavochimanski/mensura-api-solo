from fastapi import APIRouter, Depends, Body, Path, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.receitas.services.service_receitas import ReceitasService
from app.api.receitas.schemas.schema_receitas import (
    IngredienteIn,
    IngredienteOut,
    AdicionalIn,
    AdicionalOut,
)
from app.database.db_connection import get_db


router = APIRouter(prefix="/api/mensura/admin/receitas", tags=["Admin - Mensura - Receitas"])


# Ingredientes
@router.get("/{cod_barras}/ingredientes", response_model=list[IngredienteOut])
def list_ingredientes(
    cod_barras: str = Path(..., description="Código de barras do produto"),
    db: Session = Depends(get_db),
):
    return ReceitasService(db).list_ingredientes(cod_barras)


@router.post("/ingredientes", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED)
def add_ingrediente(
    body: IngredienteIn,
    db: Session = Depends(get_db),
):
    return ReceitasService(db).add_ingrediente(body)


@router.put("/ingredientes/{ingrediente_id}", response_model=IngredienteOut)
def update_ingrediente(
    ingrediente_id: int = Path(...),
    quantidade: Optional[float] = Body(None),
    unidade: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    return ReceitasService(db).update_ingrediente(ingrediente_id, quantidade, unidade)


@router.delete("/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_ingrediente(
    ingrediente_id: int,
    db: Session = Depends(get_db),
):
    ReceitasService(db).remove_ingrediente(ingrediente_id)
    return {"ok": True}


# Adicionais
@router.get("/{cod_barras}/adicionais", response_model=list[AdicionalOut])
def list_adicionais(
    cod_barras: str,
    db: Session = Depends(get_db),
):
    return ReceitasService(db).list_adicionais(cod_barras)


@router.post("/adicionais", response_model=AdicionalOut, status_code=status.HTTP_201_CREATED)
def add_adicional(
    body: AdicionalIn,
    db: Session = Depends(get_db),
):
    return ReceitasService(db).add_adicional(body)


@router.put("/adicionais/{adicional_id}", response_model=AdicionalOut)
def update_adicional(
    adicional_id: int,
    preco: Optional[float] = Body(None),
    db: Session = Depends(get_db),
):
    return ReceitasService(db).update_adicional(adicional_id, preco)


@router.delete("/adicionais/{adicional_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_adicional(
    adicional_id: int,
    db: Session = Depends(get_db),
):
    ReceitasService(db).remove_adicional(adicional_id)
    return {"ok": True}




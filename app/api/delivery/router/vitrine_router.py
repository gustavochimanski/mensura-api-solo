from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status, Body, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.delivery.services.vitrines_service import VitrinesService
from app.api.delivery.schemas.schema_vitrine import (
    CriarVitrineRequest, AtualizarVitrineRequest, VitrineOut
)
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/vitrines", tags=["Delivery - Vitrines"])


class VinculoRequest(BaseModel):
    empresa_id: int
    cod_barras: str


class ToggleHomeRequest(BaseModel):
    is_home: bool


def _to_out(v) -> VitrineOut:
    cat0_id = v.categorias[0].id if getattr(v, "categorias", None) else None
    return VitrineOut(
        id=v.id,
        cod_categoria=cat0_id,
        titulo=v.titulo,
        slug=v.slug,
        ordem=v.ordem,
        is_home=bool(getattr(v, "is_home", False)),
    )


# --- SEARCH (coloque acima das rotas dinâmicas para evitar conflito) ---
@router.get("/search", response_model=List[VitrineOut])
def search_vitrines(
    q: Optional[str] = Query(None, description="Busca por título/slug"),
    cod_categoria: Optional[int] = Query(None, description="Filtra por categoria vinculada"),
    is_home: Optional[bool] = Query(None, description="Filtra por destaque da home"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    svc = VitrinesService(db)
    vitrines = svc.search(q=q, cod_categoria=cod_categoria, is_home=is_home, limit=limit, offset=offset)
    return [_to_out(v) for v in vitrines]


# --- Toggle Home ---
@router.patch("/{vitrine_id}/home", response_model=VitrineOut)
def toggle_home_vitrine(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    payload: ToggleHomeRequest = Body(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Vitrines] Set is_home={payload.is_home} ID={vitrine_id}")
    svc = VitrinesService(db)
    v = svc.set_is_home(vitrine_id, payload.is_home)
    return _to_out(v)


# --- CRUD ---
@router.post("", response_model=VitrineOut, status_code=status.HTTP_201_CREATED)
def criar_vitrine(
    request: CriarVitrineRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Criando - categoria={request.cod_categoria} titulo={request.titulo}")
    svc = VitrinesService(db)
    v = svc.create(request)
    return _to_out(v)


@router.put("/{vitrine_id}", response_model=VitrineOut)
def atualizar_vitrine(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    request: AtualizarVitrineRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Atualizando ID={vitrine_id} payload={request.model_dump(exclude_none=True)}")
    svc = VitrinesService(db)
    v = svc.update(vitrine_id, request)
    return _to_out(v)


@router.delete("/{vitrine_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_vitrine(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Deletando ID={vitrine_id}")
    svc = VitrinesService(db)
    svc.delete(vitrine_id)
    return None


# --- Vínculos produto ↔ vitrine ---
@router.post("/{vitrine_id}/vincular", status_code=status.HTTP_204_NO_CONTENT)
def vincular_produto(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    payload: VinculoRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Vincular - vitrine={vitrine_id}, empresa={payload.empresa_id}, produto={payload.cod_barras}")
    svc = VitrinesService(db)
    svc.vincular_produto(vitrine_id=vitrine_id, empresa_id=payload.empresa_id, cod_barras=payload.cod_barras)
    return None


@router.delete("/{vitrine_id}/vincular/{cod_barras}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_produto(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    cod_barras: str = Path(..., description="Código de barras do produto"),
    empresa_id: int = Query(..., description="Empresa do vínculo"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Desvincular - vitrine={vitrine_id}, empresa={empresa_id}, produto={cod_barras}")
    svc = VitrinesService(db)
    svc.desvincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
    return None

from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status, Body, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.cardapio.services.service_vitrines import VitrinesService
from app.api.cardapio.services.service_vitrines_landingpage_store import VitrinesLandingpageStoreService
from app.api.cardapio.schemas.schema_vitrine import (
    CriarVitrineRequest, AtualizarVitrineRequest, VitrineOut
)
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/cardapio/admin/vitrines", tags=["Admin - Cardápio - Vitrines"], dependencies=[Depends(get_current_user)])


class VinculoRequest(BaseModel):
    empresa_id: int                 
    cod_barras: str


class VinculoReceitaRequest(BaseModel):
    receita_id: int


class ToggleHomeRequest(BaseModel):
    is_home: bool


def _to_out(v) -> VitrineOut:
    cat0_id = v.categorias[0].id if getattr(v, "categorias", None) and len(v.categorias) > 0 else None
    return VitrineOut(
        id=v.id,
        cod_categoria=cat0_id,  # Pode ser None
        titulo=v.titulo,
        slug=v.slug,
        ordem=v.ordem,
        is_home=bool(getattr(v, "is_home", False)),
    )


# --- SEARCH (coloque acima das rotas dinâmicas para evitar conflito) ---
@router.get("/search", response_model=List[VitrineOut])
def search_vitrines(
    empresa_id: int = Query(..., description="ID da empresa"),
    q: Optional[str] = Query(None, description="Busca por título/slug"),
    cod_categoria: Optional[int] = Query(None, description="Filtra por categoria vinculada"),
    is_home: Optional[bool] = Query(None, description="Filtra por destaque da home"),
    landingpage_true: bool = Query(False, description="Se true, opera em vitrines_landingpage_store (sem categoria)"),
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        vitrines = svc.search(empresa_id=empresa_id, q=q, is_home=is_home, limit=limit, offset=offset)
        return [
            VitrineOut(
                id=v.id,
                cod_categoria=None,
                titulo=v.titulo,
                slug=v.slug,
                ordem=v.ordem,
                is_home=bool(getattr(v, "is_home", False)),
            )
            for v in vitrines
        ]
    else:
        svc = VitrinesService(db)
        vitrines = svc.search(empresa_id=empresa_id, q=q, cod_categoria=cod_categoria, is_home=is_home, limit=limit, offset=offset)
        return [_to_out(v) for v in vitrines]


# --- Toggle Home ---
@router.patch("/{vitrine_id}/home", response_model=VitrineOut)
def toggle_home_vitrine(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, opera em vitrines_landingpage_store (sem categoria)"),
    payload: ToggleHomeRequest = Body(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Vitrines] Set is_home={payload.is_home} ID={vitrine_id}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        v = svc.set_is_home(vitrine_id, payload.is_home, empresa_id=empresa_id)
        return VitrineOut(
            id=v.id,
            cod_categoria=None,
            titulo=v.titulo,
            slug=v.slug,
            ordem=v.ordem,
            is_home=bool(getattr(v, "is_home", False)),
        )
    else:
        svc = VitrinesService(db)
        v = svc.set_is_home(vitrine_id, payload.is_home, empresa_id=empresa_id)
        return _to_out(v)


# --- CRUD ---
@router.post("/", response_model=VitrineOut, status_code=status.HTTP_201_CREATED)
def criar_vitrine(
    request: CriarVitrineRequest,
    landingpage_true: bool = Query(False, description="Se true, cria em vitrines_landingpage_store (sem categoria)"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Criando - categoria={request.cod_categoria} titulo={request.titulo}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        v = svc.create(request)
        return VitrineOut(
            id=v.id,
            cod_categoria=None,
            titulo=v.titulo,
            slug=v.slug,
            ordem=v.ordem,
            is_home=bool(getattr(v, "is_home", False)),
        )
    else:
        svc = VitrinesService(db)
        v = svc.create(request)
        return _to_out(v)


@router.put("/{vitrine_id}", response_model=VitrineOut)
def atualizar_vitrine(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, atualiza em vitrines_landingpage_store (sem categoria)"),
    request: AtualizarVitrineRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Atualizando ID={vitrine_id} payload={request.model_dump(exclude_none=True)}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        v = svc.update(vitrine_id, request, empresa_id=empresa_id)
        return VitrineOut(
            id=v.id,
            cod_categoria=None,
            titulo=v.titulo,
            slug=v.slug,
            ordem=v.ordem,
            is_home=bool(getattr(v, "is_home", False)),
        )
    else:
        svc = VitrinesService(db)
        v = svc.update(vitrine_id, request, empresa_id=empresa_id)
        return _to_out(v)


@router.delete("/{vitrine_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_vitrine(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, deleta em vitrines_landingpage_store (sem categoria)"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Deletando ID={vitrine_id}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.delete(vitrine_id, empresa_id=empresa_id)
    else:
        svc = VitrinesService(db)
        svc.delete(vitrine_id, empresa_id=empresa_id)
    return None


# --- Vínculos combo ↔ vitrine (rotas mais específicas primeiro) ---
class VinculoComboRequest(BaseModel):
    combo_id: int


@router.post("/{vitrine_id}/vincular-combo", status_code=status.HTTP_204_NO_CONTENT)
def vincular_combo(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, vincula em vitrines_landingpage_store"),
    payload: VinculoComboRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Vincular combo - vitrine={vitrine_id}, combo={payload.combo_id}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.vincular_combo(vitrine_id=vitrine_id, combo_id=payload.combo_id, empresa_id=empresa_id)
    else:
        svc = VitrinesService(db)
        svc.vincular_combo(vitrine_id=vitrine_id, combo_id=payload.combo_id, empresa_id=empresa_id)
    return None


@router.delete("/{vitrine_id}/vincular-combo/{combo_id}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_combo(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    combo_id: int = Path(..., description="ID do combo"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, desvincula em vitrines_landingpage_store"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Desvincular combo - vitrine={vitrine_id}, combo={combo_id}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.desvincular_combo(vitrine_id=vitrine_id, combo_id=combo_id, empresa_id=empresa_id)
    else:
        svc = VitrinesService(db)
        svc.desvincular_combo(vitrine_id=vitrine_id, combo_id=combo_id, empresa_id=empresa_id)
    return None


# --- Vínculos receita ↔ vitrine (rotas mais específicas primeiro) ---
@router.post("/{vitrine_id}/vincular-receita", status_code=status.HTTP_204_NO_CONTENT)
def vincular_receita(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, vincula em vitrines_landingpage_store"),
    payload: VinculoReceitaRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Vincular receita - vitrine={vitrine_id}, receita={payload.receita_id}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.vincular_receita(vitrine_id=vitrine_id, receita_id=payload.receita_id, empresa_id=empresa_id)
    else:
        svc = VitrinesService(db)
        svc.vincular_receita(vitrine_id=vitrine_id, receita_id=payload.receita_id, empresa_id=empresa_id)
    return None


@router.delete("/{vitrine_id}/vincular-receita/{receita_id}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_receita(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    receita_id: int = Path(..., description="ID da receita"),
    empresa_id: int = Query(..., description="ID da empresa"),
    landingpage_true: bool = Query(False, description="Se true, desvincula em vitrines_landingpage_store"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Desvincular receita - vitrine={vitrine_id}, receita={receita_id}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.desvincular_receita(vitrine_id=vitrine_id, receita_id=receita_id, empresa_id=empresa_id)
    else:
        svc = VitrinesService(db)
        svc.desvincular_receita(vitrine_id=vitrine_id, receita_id=receita_id, empresa_id=empresa_id)
    return None


# --- Vínculos produto ↔ vitrine (rota menos específica por último) ---
@router.post("/{vitrine_id}/vincular", status_code=status.HTTP_204_NO_CONTENT)
def vincular_produto(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    landingpage_true: bool = Query(False, description="Se true, vincula em vitrines_landingpage_store"),
    payload: VinculoRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Vincular - vitrine={vitrine_id}, empresa={payload.empresa_id}, produto={payload.cod_barras}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.vincular_produto(vitrine_id=vitrine_id, empresa_id=payload.empresa_id, cod_barras=payload.cod_barras)
    else:
        svc = VitrinesService(db)
        svc.vincular_produto(vitrine_id=vitrine_id, empresa_id=payload.empresa_id, cod_barras=payload.cod_barras)
    return None


@router.delete("/{vitrine_id}/vincular/{cod_barras}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_produto(
    vitrine_id: int = Path(..., description="ID da vitrine"),
    cod_barras: str = Path(..., description="Código de barras do produto"),
    empresa_id: int = Query(..., description="Empresa do vínculo"),
    landingpage_true: bool = Query(False, description="Se true, desvincula em vitrines_landingpage_store"),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Desvincular - vitrine={vitrine_id}, empresa={empresa_id}, produto={cod_barras}")
    if landingpage_true:
        svc = VitrinesLandingpageStoreService(db)
        svc.desvincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
    else:
        svc = VitrinesService(db)
        svc.desvincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
    return None
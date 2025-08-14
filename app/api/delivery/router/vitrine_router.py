from fastapi import APIRouter, Depends, Query, status, Body, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

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

def _to_out(nova) -> VitrineOut:
    cat0_id = nova.categorias[0].id if getattr(nova, "categorias", None) else None
    return VitrineOut(
        id=nova.id,
        cod_categoria=cat0_id,
        titulo=nova.titulo,
        slug=nova.slug,
        ordem=nova.ordem,
        is_home=bool(getattr(nova, "is_home", False)),
    )

@router.post("", response_model=VitrineOut, status_code=status.HTTP_201_CREATED)
def criar_vitrine(
    request: CriarVitrineRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Criando - categoria={request.cod_categoria} titulo={request.titulo}")
    svc = VitrinesService(db)
    nova = svc.create(request)
    return _to_out(nova)

@router.put("/{vitrine_id}", response_model=VitrineOut)
def atualizar_vitrine(
    vitrine_id: int,
    request: AtualizarVitrineRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Atualizando ID={vitrine_id} payload={request.model_dump(exclude_none=True)}")
    svc = VitrinesService(db)
    v = svc.update(vitrine_id, request)
    return _to_out(v)

@router.delete("/{vitrine_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_vitrine(
    vitrine_id: int = Path(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Deletando ID={vitrine_id}")
    svc = VitrinesService(db)
    svc.delete(vitrine_id)
    return None

@router.post("/{vitrine_id}/vincular", status_code=status.HTTP_204_NO_CONTENT)
def vincular_produto(
    vitrine_id: int,
    payload: VinculoRequest = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Vincular - vitrine={vitrine_id}, empresa={payload.empresa_id}, produto={payload.cod_barras}")
    svc = VitrinesService(db)
    svc.vincular_produto(vitrine_id=vitrine_id, empresa_id=payload.empresa_id, cod_barras=payload.cod_barras)
    return None

@router.delete("/{vitrine_id}/vincular/{cod_barras}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_produto(
    vitrine_id: int,
    cod_barras: str,
    empresa_id: int = Query(...),
    db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Desvincular - vitrine={vitrine_id}, empresa={empresa_id}, produto={cod_barras}")
    svc = VitrinesService(db)
    svc.desvincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
    return None

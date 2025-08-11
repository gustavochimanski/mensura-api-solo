from fastapi import APIRouter, Depends, Query, status, Body, Path
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.api.delivery.services.vitrines_service import VitrinesService
from app.api.delivery.schemas.vitrine_schema import (
    CriarVitrineRequest, CriarVitrineResponse
)
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/vitrines", tags=["Delivery - Vitrines"])

class VinculoRequest(BaseModel):
    empresa_id: int
    cod_barras: str

@router.get("", response_model=List[CriarVitrineResponse])
def listar_vitrines(
        empresa_id: int = Query(..., description="ID da empresa"),
        cod_categoria: Optional[int] = Query(None, description="Filtrar por ID da categoria"),
        db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Listando - empresa_id={empresa_id}, cod_categoria={cod_categoria}")
    svc = VitrinesService(db)
    vitrines = svc.listar(empresa_id=empresa_id, cod_categoria=cod_categoria)
    return [CriarVitrineResponse.from_orm(v) for v in vitrines]

@router.post("", response_model=CriarVitrineResponse, status_code=status.HTTP_201_CREATED)
def criar_vitrine(
        request: CriarVitrineRequest,
        db: Session = Depends(get_db)
):
    logger.info(f"[Vitrines] Criando - categoria={request.cod_categoria} titulo={request.titulo}")
    svc = VitrinesService(db)
    nova = svc.create(request)
    return CriarVitrineResponse.model_validate(nova)

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
    """
    Vincula um produto (empresa x cod_barras) à vitrine.
    """
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
    """
    Desvincula um produto (empresa x cod_barras) da vitrine.
    """
    logger.info(f"[Vitrines] Desvincular - vitrine={vitrine_id}, empresa={empresa_id}, produto={cod_barras}")
    svc = VitrinesService(db)
    svc.desvincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
    return None

from fastapi import APIRouter, Depends, Query, Path, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.db_connection import get_db
from app.api.delivery.services.cupom_service import CuponsService
from app.api.delivery.schemas.cupom_dv_schema import (
    CupomOut, CupomCreate, CupomUpdate
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cupons", tags=["Delivery - Cupons"])

@router.get("", response_model=List[CupomOut])
def listar_cupons(
    empresa_id: int = Query(..., description="ID da empresa"),
    ativo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Busca por código ou descrição"),
    db: Session = Depends(get_db),
):
    """
    Lista cupons da empresa; pode filtrar por ativo e fazer busca básica.
    """
    logger.info(f"[Cupons] Listar - empresa={empresa_id} ativo={ativo} search={search}")
    svc = CuponsService(db)
    return svc.list(empresa_id=empresa_id, ativo=ativo, search=search)

@router.get("/{cupom_id}", response_model=CupomOut)
def obter_cupom(
    cupom_id: int = Path(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Cupons] Get - id={cupom_id}")
    svc = CuponsService(db)
    return svc.get(cupom_id)

@router.get("/by-code/{codigo}", response_model=CupomOut)
def obter_por_codigo(
    codigo: str,
    empresa_id: int = Query(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Cupons] Get by code - code={codigo} empresa={empresa_id}")
    svc = CuponsService(db)
    cupom = svc.get_by_code(empresa_id=empresa_id, codigo=codigo)
    if not cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    return cupom

@router.post("", response_model=CupomOut, status_code=status.HTTP_201_CREATED)
def criar_cupom(
    payload: CupomCreate,
    db: Session = Depends(get_db),
):
    logger.info(f"[Cupons] Criar - code={payload.codigo}")
    svc = CuponsService(db)
    return svc.create(payload)

@router.put("/{cupom_id}", response_model=CupomOut)
def atualizar_cupom(
    cupom_id: int,
    payload: CupomUpdate,
    db: Session = Depends(get_db),
):
    logger.info(f"[Cupons] Update - id={cupom_id}")
    svc = CuponsService(db)
    return svc.update(cupom_id, payload)

@router.delete("/{cupom_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cupom(
    cupom_id: int,
    db: Session = Depends(get_db),
):
    logger.info(f"[Cupons] Delete - id={cupom_id}")
    svc = CuponsService(db)
    svc.delete(cupom_id)
    return None

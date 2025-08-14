from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database.db_connection import get_db
from app.api.delivery.services.entregadores_service import EntregadoresService
from app.api.delivery.schemas.schema_entregador_dv import (
    EntregadorOut, EntregadorCreate, EntregadorUpdate
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/entregadores", tags=["Delivery - Entregadores"])

@router.get("", response_model=List[EntregadorOut])
def listar_entregadores(
    empresa_id: int = Query(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Listar - empresa={empresa_id}")
    svc = EntregadoresService(db)
    return svc.list(empresa_id)

@router.get("/{entregador_id}", response_model=EntregadorOut)
def get_entregador(
    entregador_id: int = Path(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Get - id={entregador_id}")
    svc = EntregadoresService(db)
    return svc.get(entregador_id)

@router.post("", response_model=EntregadorOut, status_code=status.HTTP_201_CREATED)
def criar_entregador(
    payload: EntregadorCreate,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Criar - {payload.nome}")
    svc = EntregadoresService(db)
    return svc.create(payload)

@router.put("/{entregador_id}", response_model=EntregadorOut)
def atualizar_entregador(
    entregador_id: int,
    payload: EntregadorUpdate,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Update - id={entregador_id}")
    svc = EntregadoresService(db)
    return svc.update(entregador_id, payload)

@router.delete("/{entregador_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_entregador(
    entregador_id: int,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Delete - id={entregador_id}")
    svc = EntregadoresService(db)
    svc.delete(entregador_id)
    return None

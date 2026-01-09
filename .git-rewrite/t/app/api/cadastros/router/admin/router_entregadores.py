from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database.db_connection import get_db
from app.api.cadastros.services.service_entregadores import EntregadoresService
from app.api.cadastros.schemas.schema_entregador import (
    EntregadorOut, EntregadorCreate, EntregadorUpdate
)
from app.utils.logger import logger
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/cadastros/admin/entregadores", tags=["Admin - Cadastros - Entregadores"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=List[EntregadorOut])
def listar_entregadores(
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Listar ")
    svc = EntregadoresService(db)
    return svc.list()

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

@router.post("/{entregador_id}/vincular_empresa", response_model=EntregadorOut)
def vincular_entregador_empresa(
    entregador_id: int,
    empresa_id: int = Query(..., description="ID da empresa a ser vinculada"),
    db: Session = Depends(get_db),
):
    svc = EntregadoresService(db)
    return svc.vincular_empresa(entregador_id, empresa_id)

@router.delete("/{entregador_id}/vincular_empresa", response_model=EntregadorOut)
def desvincular_entregador_empresa(
    entregador_id: int,
    empresa_id: int = Query(..., description="ID da empresa a ser desvinculada"),
    db: Session = Depends(get_db),
):
    svc = EntregadoresService(db)
    return svc.desvincular_empresa(entregador_id, empresa_id)


@router.delete("/{entregador_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_entregador(
    entregador_id: int,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Delete - id={entregador_id}")
    svc = EntregadoresService(db)
    svc.delete(entregador_id)
    return None

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.api.delivery.services.service_endereco_dv import EnderecosService
from app.core.dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.delivery.schemas.schema_endereco_dv import (
  EnderecoOut , EnderecoCreate, EnderecoUpdate
)
from app.utils.logger import logger

# --- Controller ---
router = APIRouter(prefix="/api/delivery/enderecos", tags=["Delivery - Endereços"])

@router.get("", response_model=List[EnderecoOut])
def listar_enderecos(
    cliente_id: int = Query(...),
    db: Session = Depends(get_db), dependencies=[Depends(get_current_user)]

):
    logger.info(f"[Enderecos] Listar - cliente={cliente_id}")
    svc = EnderecosService(db)
    return svc.list(cliente_id)

@router.get("/{endereco_id}", response_model=EnderecoOut)
def get_endereco(
    endereco_id: int = Path(...),
    db: Session = Depends(get_db), dependencies=[Depends(get_current_user)]
):
    logger.info(f"[Enderecos] Get - id={endereco_id}")
    svc = EnderecosService(db)
    return svc.get(endereco_id)

@router.post("", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_endereco(
    payload: EnderecoCreate,
    db: Session = Depends(get_db),
):
    logger.info("[Enderecos] Criar")
    svc = EnderecosService(db)
    return svc.create(payload)

@router.put("/{endereco_id}", response_model=EnderecoOut)
def atualizar_endereco(
    endereco_id: int,
    payload: EnderecoUpdate,
    db: Session = Depends(get_db), dependencies=[Depends(get_current_user)]
):
    logger.info(f"[Enderecos] Update - id={endereco_id}")
    svc = EnderecosService(db)
    return svc.update(endereco_id, payload)

@router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_endereco(
    endereco_id: int,
    db: Session = Depends(get_db), dependencies=[Depends(get_current_user)]
):
    logger.info(f"[Enderecos] Delete - id={endereco_id}")
    svc = EnderecosService(db)
    svc.delete(endereco_id)
    return None

@router.post("/{endereco_id}/set-padrao", response_model=EnderecoOut)
def set_endereco_padrao(
    endereco_id: int,
    cliente_id: int = Query(...),
    db: Session = Depends(get_db), dependencies=[Depends(get_current_user)]
):
    logger.info(f"[Enderecos] Set padrão - id={endereco_id} cliente={cliente_id}")
    svc = EnderecosService(db)
    return svc.set_padrao(cliente_id, endereco_id)

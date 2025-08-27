from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session
from typing import List
from app.api.delivery.services.service_endereco_dv import EnderecosService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.delivery.schemas.schema_endereco_dv import EnderecoOut, EnderecoCreate, EnderecoUpdate
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/enderecos", tags=["Delivery - Endereços"])

@router.get("", response_model=List[EnderecoOut])
def listar_enderecos(
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Enderecos] Listar - cliente={cliente.super_token}")
    svc = EnderecosService(db)
    return svc.list(cliente.super_token)

@router.get("/{endereco_id}", response_model=EnderecoOut)
def get_endereco(
    endereco_id: int = Path(...),
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Enderecos] Get - id={endereco_id} cliente={cliente.super_token}")
    svc = EnderecosService(db)
    return svc.get(cliente.super_token, endereco_id)

@router.post("", response_model=EnderecoOut, status_code=status.HTTP_201_CREATED)
def criar_endereco(
    payload: EnderecoCreate,
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Enderecos] Criar - cliente={cliente.super_token}")
    svc = EnderecosService(db)
    return svc.create(cliente.super_token, payload)

@router.put("/{endereco_id}", response_model=EnderecoOut)
def atualizar_endereco(
    endereco_id: int,
    payload: EnderecoUpdate,
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Enderecos] Update - id={endereco_id} cliente={cliente.super_token}")
    svc = EnderecosService(db)
    return svc.update(cliente.super_token, endereco_id, payload)

@router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_endereco(
    endereco_id: int,
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Enderecos] Delete - id={endereco_id} cliente={cliente.super_token}")
    svc = EnderecosService(db)
    svc.delete(cliente.super_token, endereco_id)
    return None

@router.post("/{endereco_id}/set-padrao", response_model=EnderecoOut)
def set_endereco_padrao(
    endereco_id: int,
    cliente=Depends(get_cliente_by_super_token),
    db: Session = Depends(get_db)
):
    logger.info(f"[Enderecos] Set padrão - id={endereco_id} cliente={cliente.super_token}")
    svc = EnderecosService(db)
    return svc.set_padrao(cliente.super_token, endereco_id)

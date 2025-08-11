from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database.db_connection import get_db
from app.api.delivery.schemas.endereco_dv_schema import (
  EnderecoOut , EnderecoCreate, EnderecoUpdate
)
from app.utils.logger import logger

# --- Services/Repos mínimos (criados) ---
from sqlalchemy.orm import joinedload
from app.api.delivery.models.endereco_dv_model import EnderecoDeliveryModel  # ajuste o path exato se diferente
from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel    # ajuste o path exato se diferente

class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_cliente(self, cliente_id: int) -> List[EnderecoDeliveryModel]:
        return (
            self.db.query(EnderecoDeliveryModel)
            .options(joinedload(EnderecoDeliveryModel.cliente))
            .filter(EnderecoDeliveryModel.cliente_id == cliente_id)
            .order_by(EnderecoDeliveryModel.created_at.desc())
            .all()
        )

    def get(self, end_id: int) -> EnderecoDeliveryModel:
        obj = (
            self.db.query(EnderecoDeliveryModel)
            .filter(EnderecoDeliveryModel.id == end_id)
            .first()
        )
        if not obj:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return obj

    def create(self, payload: EnderecoCreate) -> EnderecoDeliveryModel:
        obj = EnderecoDeliveryModel(**payload.model_dump())
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, end_id: int, payload: EnderecoUpdate) -> EnderecoDeliveryModel:
        obj = self.get(end_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, end_id: int) -> None:
        obj = self.get(end_id)
        self.db.delete(obj)
        self.db.commit()

    def set_padrao(self, cliente_id: int, end_id: int) -> EnderecoDeliveryModel:
        # zera padrão dos demais
        self.db.query(EnderecoDeliveryModel).filter(
            EnderecoDeliveryModel.cliente_id == cliente_id
        ).update({"padrao": False})
        # define padrão no escolhido
        obj = self.get(end_id)
        obj.padrao = True
        self.db.commit()
        self.db.refresh(obj)
        return obj

class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, cliente_id: int):
        return [EnderecoOut.from_orm(x) for x in self.repo.list_by_cliente(cliente_id)]

    def get(self, end_id: int):
        return EnderecoOut.from_orm(self.repo.get(end_id))

    def create(self, payload: EnderecoCreate):
        return EnderecoOut.from_orm(self.repo.create(payload))

    def update(self, end_id: int, payload: EnderecoUpdate):
        return EnderecoOut.from_orm(self.repo.update(end_id, payload))

    def delete(self, end_id: int):
        self.repo.delete(end_id)

    def set_padrao(self, cliente_id: int, end_id: int):
        return EnderecoOut.from_orm(self.repo.set_padrao(cliente_id, end_id))

# --- Controller ---
router = APIRouter(prefix="/api/delivery/enderecos", tags=["Delivery - Endereços"])

@router.get("", response_model=List[EnderecoOut])
def listar_enderecos(
    cliente_id: int = Query(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Enderecos] Listar - cliente={cliente_id}")
    svc = EnderecosService(db)
    return svc.list(cliente_id)

@router.get("/{endereco_id}", response_model=EnderecoOut)
def get_endereco(
    endereco_id: int = Path(...),
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
):
    logger.info(f"[Enderecos] Update - id={endereco_id}")
    svc = EnderecosService(db)
    return svc.update(endereco_id, payload)

@router.delete("/{endereco_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_endereco(
    endereco_id: int,
    db: Session = Depends(get_db),
):
    logger.info(f"[Enderecos] Delete - id={endereco_id}")
    svc = EnderecosService(db)
    svc.delete(endereco_id)
    return None

@router.post("/{endereco_id}/set-padrao", response_model=EnderecoOut)
def set_endereco_padrao(
    endereco_id: int,
    cliente_id: int = Query(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Enderecos] Set padrão - id={endereco_id} cliente={cliente_id}")
    svc = EnderecosService(db)
    return svc.set_padrao(cliente_id, endereco_id)

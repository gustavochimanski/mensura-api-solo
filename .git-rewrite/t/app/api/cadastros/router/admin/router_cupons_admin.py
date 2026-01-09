from fastapi import APIRouter, Depends, Path, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.db_connection import get_db
from app.api.cadastros.services.service_cupom import CuponsService
from app.api.cadastros.schemas.schema_cupom import (
    CupomOut, CupomCreate, CupomUpdate
)
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/delivery/admin/cupons",
    tags=["Admin - Delivery - Cupons"],
    dependencies=[Depends(get_current_user)]
)

@router.get("", response_model=List[CupomOut])
def listar_cupons(
    parceiro_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    svc = CuponsService(db)
    if parceiro_id is not None:
        return svc.list_by_parceiro(parceiro_id)
    return svc.list()

@router.get("/{cupom_id}", response_model=CupomOut)
def obter_cupom(cupom_id: int = Path(...), db: Session = Depends(get_db)):
    svc = CuponsService(db)
    return svc.get(cupom_id)

@router.get("/by-code/{codigo}", response_model=CupomOut)
def obter_por_codigo(
    codigo: str,
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    svc = CuponsService(db)
    cupom = svc.repo.get_by_code(codigo, empresa_id=empresa_id)
    if not cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    return cupom

@router.post("", response_model=CupomOut, status_code=status.HTTP_201_CREATED)
def criar_cupom(payload: CupomCreate, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    return svc.create(payload)

@router.put("/{cupom_id}", response_model=CupomOut)
def atualizar_cupom(cupom_id: int, payload: CupomUpdate, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    return svc.update(cupom_id, payload)

@router.delete("/{cupom_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cupom(cupom_id: int, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    svc.delete(cupom_id)
    return None

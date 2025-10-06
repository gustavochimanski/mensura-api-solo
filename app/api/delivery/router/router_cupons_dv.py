from fastapi import APIRouter, Depends, Path, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.db_connection import get_db
from app.api.delivery.services.service_cupom import CuponsService
from app.api.delivery.schemas.schema_cupom import (
    CupomOut, CupomCreate, CupomUpdate, CupomLinkCreate, CupomLinkOut
)

router = APIRouter(prefix="/api/delivery/cupons", tags=["Cupons - Admin - Delivery"])

def map_link_out(link_model) -> CupomLinkOut:
    return CupomLinkOut(
        id=link_model.id,
        cupom_id=link_model.cupom_id,
        titulo=link_model.titulo,
        url=link_model.url
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
def obter_por_codigo(codigo: str, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    cupom = svc.repo.get_by_code(codigo)
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

# ---------------- LINKS ----------------

@router.get("/links/{cupom_id}", response_model=List[CupomLinkOut])
def listar_links(cupom_id: int, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    links = svc.list_links(cupom_id)
    return [map_link_out(l) for l in links]

@router.post("/links/{cupom_id}", response_model=CupomLinkOut, status_code=status.HTTP_201_CREATED)
def criar_link(cupom_id: int, payload: CupomLinkCreate, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    link = svc.add_link(cupom_id, payload.titulo, payload.url)
    return map_link_out(link)

@router.put("/links/{link_id}", response_model=CupomLinkOut)
def atualizar_link(link_id: int, payload: CupomLinkCreate, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    link = svc.update_link(link_id, titulo=payload.titulo, url=payload.url)
    return map_link_out(link)

@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_link(link_id: int, db: Session = Depends(get_db)):
    svc = CuponsService(db)
    svc.delete_link(link_id)
    return None

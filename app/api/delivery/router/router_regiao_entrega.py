from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.delivery.schemas.schema_regiao_entrega import RegiaoEntregaCreate, RegiaoEntregaUpdate, RegiaoEntregaOut
from app.api.delivery.services.service_regiao_entrega import RegiaoEntregaService
from app.database.db_connection import get_db
from app.utils.geopapify_client import GeoapifyClient

router = APIRouter(prefix="/api/delivery/regioes-entrega", tags=["Regiões de Entrega - Admin - Delivery"])

@router.get("/{empresa_id}", response_model=list[RegiaoEntregaOut])
def list_regioes(empresa_id: int, db: Session = Depends(get_db)):
    return RegiaoEntregaService(db).list(empresa_id)

@router.get("/detalhe/{regiao_id}", response_model=RegiaoEntregaOut)
def get_regiao(regiao_id: int, db: Session = Depends(get_db)):
    return RegiaoEntregaService(db).get(regiao_id)

@router.post("/", response_model=RegiaoEntregaOut)
async def create_regiao(payload: RegiaoEntregaCreate, db: Session = Depends(get_db)):
    return await RegiaoEntregaService(db).create(payload)

@router.put("/{regiao_id}", response_model=RegiaoEntregaOut)
async def update_regiao(regiao_id: int, payload: RegiaoEntregaUpdate, db: Session = Depends(get_db)):
    return await RegiaoEntregaService(db).update(regiao_id, payload)

@router.delete("/{regiao_id}")
def delete_regiao(regiao_id: int, db: Session = Depends(get_db)):
    return RegiaoEntregaService(db).delete(regiao_id)

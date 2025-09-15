# app/api/mensura/router/router_impressora.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.db_connection import get_db
from app.api.mensura.schemas.schema_impressora import ImpressoraCreate, ImpressoraUpdate, ImpressoraResponse
from app.api.mensura.services.impressora_service import ImpressoraService

router = APIRouter(prefix="/api/mensura/impressoras", tags=["Impressoras"])

# Criar impressora
@router.post("/", response_model=ImpressoraResponse)
async def create_impressora(
    impressora_data: ImpressoraCreate,
    db: Session = Depends(get_db)
):
    try:
        return ImpressoraService(db).create_impressora(impressora_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Obter impressora por ID
@router.get("/{impressora_id}", response_model=ImpressoraResponse)
def get_impressora(impressora_id: int, db: Session = Depends(get_db)):
    impressora = ImpressoraService(db).get_impressora(impressora_id)
    if not impressora:
        raise HTTPException(status_code=404, detail="Impressora não encontrada")
    return impressora

# Listar impressoras por empresa
@router.get("/empresa/{empresa_id}", response_model=List[ImpressoraResponse])
def get_impressoras_by_empresa(empresa_id: int, db: Session = Depends(get_db)):
    return ImpressoraService(db).get_impressoras_by_empresa(empresa_id)

# Listar todas as impressoras
@router.get("/", response_model=List[ImpressoraResponse])
def list_impressoras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return ImpressoraService(db).list_impressoras(skip, limit)

# Atualizar impressora
@router.put("/{impressora_id}", response_model=ImpressoraResponse)
def update_impressora(
    impressora_id: int,
    impressora_data: ImpressoraUpdate,
    db: Session = Depends(get_db)
):
    impressora = ImpressoraService(db).update_impressora(impressora_id, impressora_data)
    if not impressora:
        raise HTTPException(status_code=404, detail="Impressora não encontrada")
    return impressora

# Deletar impressora
@router.delete("/{impressora_id}", status_code=204)
def delete_impressora(impressora_id: int, db: Session = Depends(get_db)):
    success = ImpressoraService(db).delete_impressora(impressora_id)
    if not success:
        raise HTTPException(status_code=404, detail="Impressora não encontrada")

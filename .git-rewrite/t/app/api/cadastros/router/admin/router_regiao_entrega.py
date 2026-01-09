from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.cadastros.schemas.schema_regiao_entrega import RegiaoEntregaCreate, RegiaoEntregaUpdate, RegiaoEntregaOut
from app.api.cadastros.services.service_regiao_entrega import RegiaoEntregaService
from app.database.db_connection import get_db
# Google Maps será usado quando necessário para geocodificação
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/cadastros/admin/regioes-entrega", tags=["Admin - Cadastros - Regiões de Entrega"], 
dependencies=[Depends(get_current_user)])

@router.get("/{empresa_id}", response_model=list[RegiaoEntregaOut])
def list_regioes(empresa_id: int, db: Session = Depends(get_db)):
    return RegiaoEntregaService(db).list(empresa_id)    

@router.get("/detalhes/{regiao_id}", response_model=RegiaoEntregaOut)
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

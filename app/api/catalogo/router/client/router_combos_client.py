from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session

from app.api.catalogo.services.service_combo import CombosService
from app.database.db_connection import get_db

router = APIRouter(
    prefix="/api/catalogo/client/combos",
    tags=["Client - Catalogo - Combos"],
)


@router.get("", response_model=dict)
def listar_combos_client(
    cod_empresa: int = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = CombosService(db)
    return svc.listar(cod_empresa, page, limit, search=search)


@router.get("/{combo_id}", response_model=dict)
def obter_combo_client(combo_id: int = Path(...), db: Session = Depends(get_db)):
    svc = CombosService(db)
    return svc.obter(combo_id)


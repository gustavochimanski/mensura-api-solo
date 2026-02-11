from fastapi import APIRouter, Path, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.database.db_connection import get_db

router = APIRouter(
    prefix="/api/catalogo/public/combos",
    tags=["Public - Catalogo - Combos"],
)


@router.get("/{combo_id}", response_model=dict)
def obter_combo_public(combo_id: int = Path(...), db: Session = Depends(get_db)):  # type: ignore[name-defined]
    adapter = ComboAdapter(db)
    combo = adapter.buscar_por_id(combo_id)
    if not combo:
        raise HTTPException(status_code=404, detail="Combo não encontrado")
    return combo


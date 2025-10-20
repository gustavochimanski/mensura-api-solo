from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.relatorios.repository import RelatorioRepository
from app.api.relatorios.service import RelatoriosService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db

router = APIRouter(prefix="/relatorios", tags=["Relatórios"], dependencies=[Depends(get_current_user)])


@router.get("/panoramico-dia")
def relatorio_panoramico_dia(
    data: str = Query(..., description="Data de referência no formato YYYY-MM-DD"),
    empresa_id: int = Query(..., description="Identificador da empresa"),
    db: Session = Depends(get_db),
):
    repository = RelatorioRepository(db)
    service = RelatoriosService(repository)
    return service.relatorio_panoramico_dia(empresa_id=empresa_id, data=data)


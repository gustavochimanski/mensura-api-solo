from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.relatorios.repositories.repository import RelatorioRepository
from app.api.relatorios.services.service import RelatoriosService
from app.core.authorization import require_permissions
from app.database.db_connection import get_db

router = APIRouter(
    prefix="/api/relatorios/admin/relatorios",
    tags=["Admin - Relatórios - Panorâmico Diário"],
    # Dashboard/relatórios panorâmicos são parte do Supervisor (tela Dashboard)
    dependencies=[Depends(require_permissions(["route:/dashboard"]))],
)


@router.get("/panoramico")
def relatorio_panoramico(
    inicio: str = Query(..., description="Início do período no formato YYYY-MM-DD"),
    fim: str = Query(..., description="Fim do período no formato YYYY-MM-DD"),
    empresa_id: int = Query(..., description="Identificador da empresa"),
    db: Session = Depends(get_db),
):
    repository = RelatorioRepository(db)
    service = RelatoriosService(repository)
    return service.relatorio_panoramico_periodo(
        empresa_id=empresa_id,
        inicio=inicio,
        fim=fim,
    )


@router.get("/panoramico-dia")
def relatorio_panoramico_diario(
    data: str = Query(..., description="Dia de referência (YYYY-MM-DD)"),
    empresa_id: int = Query(..., description="Identificador da empresa"),
    db: Session = Depends(get_db),
):
    repository = RelatorioRepository(db)
    service = RelatoriosService(repository)
    return service.relatorio_diario(
        empresa_id=empresa_id,
        dia_str=data,
    )


@router.get("/panoramico/ranking-bairro")
def panoramico_ranking_bairro(
    inicio: str = Query(..., description="Início do período (YYYY-MM-DD)"),
    fim: str = Query(..., description="Fim do período (YYYY-MM-DD)"),
    empresa_id: int = Query(..., description="Identificador da empresa"),
    limite: int = Query(10, description="Quantidade de bairros no ranking"),
    db: Session = Depends(get_db),
):
    repository = RelatorioRepository(db)
    service = RelatoriosService(repository)
    return service.ranking_bairro(
        empresa_id=empresa_id,
        inicio=inicio,
        fim=fim,
        limite=limite,
    )


@router.get("/panoramico/ultimos-7-dias")
def panoramico_ultimos_7_dias(
    referencia: str = Query(..., description="Data de referência (YYYY-MM-DD) - inclui os 7 dias até ela"),
    empresa_id: int = Query(..., description="Identificador da empresa"),
    db: Session = Depends(get_db),
):
    repository = RelatorioRepository(db)
    service = RelatoriosService(repository)
    return service.ultimos_7_dias_comparativo(
        empresa_id=empresa_id,
        referencia_str=referencia,
    )


@router.get("/panoramico/pico-hora")
def panoramico_pico_hora(
    inicio: str = Query(..., description="Início do período (YYYY-MM-DD)"),
    fim: str = Query(..., description="Fim do período (YYYY-MM-DD)"),
    empresa_id: int = Query(..., description="Identificador da empresa"),
    db: Session = Depends(get_db),
):
    repository = RelatorioRepository(db)
    service = RelatoriosService(repository)
    return service.vendas_pico_hora(
        empresa_id=empresa_id,
        inicio=inicio,
        fim=fim,
    )

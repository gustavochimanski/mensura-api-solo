from fastapi import APIRouter, Depends, Body, status, Query
from sqlalchemy.orm import Session

from app.api.financeiro.schemas.schema_acerto_motoboy import (
    FecharPedidosDiretoRequest,
    FecharPedidosDiretoResponse,
    PedidoPendenteAcertoOut,
    PreviewAcertoResponse,
    AcertosPassadosResponse,
)
from app.api.financeiro.services.service_acerto_motoboy import AcertoEntregadoresService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db


router = APIRouter(
    prefix="/api/financeiro/admin/acertos-entregadores",
    tags=["Admin - Financeiro - Acertos de Entregadores"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/fechar",
    response_model=FecharPedidosDiretoResponse,
    status_code=status.HTTP_200_OK,
)
def fechar_pedidos(payload: FecharPedidosDiretoRequest = Body(...), db: Session = Depends(get_db)):
    """Fecha pedidos por período (empresa obrigatória; entregador opcional)."""
    return AcertoEntregadoresService(db).fechar_pedidos_direto(payload)


@router.get(
    "/pendentes",
    response_model=list[PedidoPendenteAcertoOut],
    status_code=status.HTTP_200_OK,
)
def listar_pendentes(
    empresa_id: int = Query(..., gt=0),
    inicio: str = Query(..., description="Início do período (YYYY-MM-DD ou ISO datetime)"),
    fim: str = Query(..., description="Fim do período (YYYY-MM-DD ou ISO datetime)"),
    entregador_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    """Lista pedidos entregues ainda não acertados no período, opcionalmente filtrando por entregador."""
    from datetime import datetime, date, time

    def parse_any(value: str, is_start: bool) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            d = date.fromisoformat(value)
            return datetime.combine(d, time.min if is_start else time.max)

    inicio_dt = parse_any(inicio, True)
    fim_dt = parse_any(fim, False)
    return AcertoEntregadoresService(db).listar_pendentes(
        empresa_id=empresa_id,
        inicio=inicio_dt,
        fim=fim_dt,
        entregador_id=entregador_id,
    )


@router.get(
    "/preview",
    response_model=PreviewAcertoResponse,
    status_code=status.HTTP_200_OK,
)
def preview_acerto(
    empresa_id: int = Query(..., gt=0),
    inicio: str = Query(...),
    fim: str = Query(...),
    entregador_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    from datetime import datetime, date, time

    def parse_any(value: str, is_start: bool) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            d = date.fromisoformat(value)
            return datetime.combine(d, time.min if is_start else time.max)

    inicio_dt = parse_any(inicio, True)
    fim_dt = parse_any(fim, False)
    return AcertoEntregadoresService(db).preview_acerto(
        empresa_id=empresa_id,
        inicio=inicio_dt,
        fim=fim_dt,
        entregador_id=entregador_id,
    )


@router.get(
    "/passados",
    response_model=AcertosPassadosResponse,
    status_code=status.HTTP_200_OK,
)
def acertos_passados(
    empresa_id: int = Query(..., gt=0),
    inicio: str = Query(...),
    fim: str = Query(...),
    entregador_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    from datetime import datetime, date, time

    def parse_any(value: str, is_start: bool) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            d = date.fromisoformat(value)
            return datetime.combine(d, time.min if is_start else time.max)

    inicio_dt = parse_any(inicio, True)
    fim_dt = parse_any(fim, False)
    return AcertoEntregadoresService(db).acertos_passados(
        empresa_id=empresa_id,
        inicio=inicio_dt,
        fim=fim_dt,
        entregador_id=entregador_id,
    )



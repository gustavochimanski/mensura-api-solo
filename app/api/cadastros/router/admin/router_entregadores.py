from datetime import datetime, date, time

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database.db_connection import get_db
from app.api.cadastros.services.service_entregadores import EntregadoresService
from app.api.cadastros.schemas.schema_entregador import (
    EntregadorOut,
    EntregadorCreate,
    EntregadorUpdate,
    EntregadorRelatorioDetalhadoOut,
)
from app.utils.logger import logger
from app.core.admin_dependencies import get_current_user

router = APIRouter(prefix="/api/cadastros/admin/entregadores", tags=["Admin - Cadastros - Entregadores"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=List[EntregadorOut])
def listar_entregadores(
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Listar ")
    svc = EntregadoresService(db)
    return svc.list()

@router.get("/{entregador_id}", response_model=EntregadorOut)
def get_entregador(
    entregador_id: int = Path(...),
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Get - id={entregador_id}")
    svc = EntregadoresService(db)
    return svc.get(entregador_id)

@router.post("", response_model=EntregadorOut, status_code=status.HTTP_201_CREATED)
def criar_entregador(
    payload: EntregadorCreate,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Criar - {payload.nome}")
    svc = EntregadoresService(db)
    return svc.create(payload)

@router.put("/{entregador_id}", response_model=EntregadorOut)
def atualizar_entregador(
    entregador_id: int,
    payload: EntregadorUpdate,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Update - id={entregador_id}")
    svc = EntregadoresService(db)
    return svc.update(entregador_id, payload)

@router.post("/{entregador_id}/vincular_empresa", response_model=EntregadorOut)
def vincular_entregador_empresa(
    entregador_id: int,
    empresa_id: int = Query(..., description="ID da empresa a ser vinculada"),
    db: Session = Depends(get_db),
):
    svc = EntregadoresService(db)
    return svc.vincular_empresa(entregador_id, empresa_id)

@router.delete("/{entregador_id}/vincular_empresa", response_model=EntregadorOut)
def desvincular_entregador_empresa(
    entregador_id: int,
    empresa_id: int = Query(..., description="ID da empresa a ser desvinculada"),
    db: Session = Depends(get_db),
):
    svc = EntregadoresService(db)
    return svc.desvincular_empresa(entregador_id, empresa_id)


@router.delete("/{entregador_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_entregador(
    entregador_id: int,
    db: Session = Depends(get_db),
):
    logger.info(f"[Entregadores] Delete - id={entregador_id}")
    svc = EntregadoresService(db)
    svc.delete(entregador_id)
    return None


def _parse_any_date_or_datetime(value: str, is_start: bool) -> datetime:
    """
    Aceita 'YYYY-MM-DD' ou datetime ISO completo e converte para datetime.
    Mesmo comportamento utilizado em rotas de acerto de entregadores.
    """
    try:
        return datetime.fromisoformat(value)
    except Exception:
        d = date.fromisoformat(value)
        return datetime.combine(d, time.min if is_start else time.max)


@router.get(
    "/{entregador_id}/relatorio-detalhado",
    response_model=EntregadorRelatorioDetalhadoOut,
    status_code=status.HTTP_200_OK,
)
def relatorio_detalhado_entregador(
    entregador_id: int = Path(..., description="ID do entregador"),
    empresa_id: int = Query(..., gt=0, description="ID da empresa para filtrar os pedidos"),
    inicio: str = Query(..., description="Início do período (YYYY-MM-DD ou ISO datetime)"),
    fim: str = Query(..., description="Fim do período (YYYY-MM-DD ou ISO datetime)"),
    db: Session = Depends(get_db),
):
    """
    Retorna um relatório detalhado do entregador no período informado:
    - quantidade de pedidos, valor total, ticket médio
    - tempo médio de entrega (aprox.), médias por dia
    - métricas de acerto (pedidos acertados e valor por dia).
    """
    inicio_dt = _parse_any_date_or_datetime(inicio, True)
    fim_dt = _parse_any_date_or_datetime(fim, False)

    logger.info(
        f"[Entregadores] Relatório detalhado - entregador_id={entregador_id}, "
        f"empresa_id={empresa_id}, inicio={inicio_dt}, fim={fim_dt}"
    )
    svc = EntregadoresService(db)
    return svc.relatorio_detalhado(
        entregador_id=entregador_id,
        empresa_id=empresa_id,
        inicio=inicio_dt,
        fim=fim_dt,
    )

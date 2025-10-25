from fastapi import (
    APIRouter, Depends, HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.mesas.services.service_mesas import MesaService
from app.api.mesas.schemas.schema_mesa import (
    MesaOut, MesaListOut, MesaStatsOut, StatusMesaEnum
)
from app.api.mesas.schemas.schema_mesa_historico import MesaHistoricoListOut
from app.api.mesas.models.model_mesa import StatusMesa
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/mesas/client/mesas",
    tags=["Client - Mesas"],
    dependencies=[Depends(get_cliente_by_super_token)]
)

# -------- ESTATÍSTICAS --------
@router.get("/stats", response_model=MesaStatsOut)
def get_mesa_stats(
    db: Session = Depends(get_db),
):
    """Retorna estatísticas das mesas"""
    service = MesaService(db)
    stats = service.get_stats()
    return MesaStatsOut(**stats)

# -------- LISTAR MESAS ATIVAS --------
@router.get("", response_model=List[MesaListOut])
def list_mesas_ativas(
    status: Optional[StatusMesaEnum] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_db),
):
    """Lista todas as mesas ativas"""
    service = MesaService(db)
    
    # Converte StatusMesaEnum para StatusMesa se necessário
    status_filter = StatusMesa(status.value) if status else None
    
    if status_filter:
        mesas = service.list_by_status(status_filter)
    else:
        mesas = service.list_all(ativa=True)
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas
    ]

# -------- BUSCAR MESA POR ID --------
@router.get("/{mesa_id}", response_model=MesaOut)
def get_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Busca mesa por ID (apenas mesas ativas)"""
    service = MesaService(db)
    mesa = service.get_by_id(mesa_id)
    
    # Verifica se a mesa está ativa
    if mesa.ativa != "S":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

# -------- BUSCAR MESA POR NÚMERO --------
@router.get("/numero/{numero}", response_model=MesaOut)
def get_mesa_by_numero(
    numero: str = Path(..., title="Número da mesa"),
    db: Session = Depends(get_db),
):
    """Busca mesa por número (apenas mesas ativas)"""
    service = MesaService(db)
    mesa = service.get_by_numero(numero)
    
    # Verifica se a mesa está ativa
    if mesa.ativa != "S":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

# -------- MESAS DISPONÍVEIS --------
@router.get("/disponiveis", response_model=List[MesaListOut])
def list_mesas_disponiveis(
    db: Session = Depends(get_db),
):
    """Lista todas as mesas disponíveis"""
    service = MesaService(db)
    mesas = service.list_by_status(StatusMesa.DISPONIVEL)
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas
    ]

# -------- MESAS OCUPADAS --------
@router.get("/ocupadas", response_model=List[MesaListOut])
def list_mesas_ocupadas(
    db: Session = Depends(get_db),
):
    """Lista todas as mesas ocupadas"""
    service = MesaService(db)
    mesas = service.list_by_status(StatusMesa.OCUPADA)
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas
    ]

# -------- MESAS RESERVADAS --------
@router.get("/reservadas", response_model=List[MesaListOut])
def list_mesas_reservadas(
    db: Session = Depends(get_db),
):
    """Lista todas as mesas reservadas"""
    service = MesaService(db)
    mesas = service.list_by_status(StatusMesa.RESERVADA)
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas
    ]

# -------- MESAS LIVRES --------
@router.get("/livres", response_model=List[MesaListOut])
def list_mesas_livres(
    db: Session = Depends(get_db),
):
    """Lista todas as mesas livres"""
    service = MesaService(db)
    mesas = service.list_by_status(StatusMesa.LIVRE)
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas
    ]

# -------- VALIDAR MESA DISPONÍVEL --------
@router.get("/{mesa_id}/disponivel")
def verificar_mesa_disponivel(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Verifica se uma mesa está disponível"""
    service = MesaService(db)
    
    try:
        mesa = service.get_by_id(mesa_id)
        is_disponivel = service.validar_mesa_disponivel(mesa_id)
        
        return {
            "mesa_id": mesa_id,
            "numero": mesa.numero,
            "disponivel": is_disponivel,
            "status": StatusMesaEnum(mesa.status.value).value,
            "status_descricao": mesa.status_descricao
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[Mesas Client] Erro ao verificar disponibilidade da mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao verificar disponibilidade da mesa: {str(e)}")

# -------- BUSCAR MESAS POR CAPACIDADE --------
@router.get("/capacidade/{capacidade_minima}", response_model=List[MesaListOut])
def list_mesas_por_capacidade(
    capacidade_minima: int = Path(..., title="Capacidade mínima", ge=1),
    db: Session = Depends(get_db),
):
    """Lista mesas com capacidade mínima especificada"""
    service = MesaService(db)
    mesas = service.list_all(ativa=True)
    
    # Filtra mesas com capacidade suficiente
    mesas_filtradas = [m for m in mesas if m.capacidade >= capacidade_minima]
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas_filtradas
    ]

# -------- HISTÓRICO DA MESA --------
@router.get("/{mesa_id}/historico", response_model=List[MesaHistoricoListOut])
def get_mesa_historico(
    mesa_id: int = Path(..., title="ID da mesa"),
    limit: int = Query(50, title="Limite de registros", ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retorna o histórico de operações de uma mesa"""
    service = MesaService(db)
    historico = service.get_historico(mesa_id, limit)
    
    return [
        MesaHistoricoListOut(
            id=h.id,
            mesa_id=h.mesa_id,
            tipo_operacao=h.tipo_operacao,
            tipo_operacao_descricao=h.tipo_operacao_descricao,
            resumo_operacao=h.resumo_operacao,
            created_at=h.created_at
        )
        for h in historico
    ]

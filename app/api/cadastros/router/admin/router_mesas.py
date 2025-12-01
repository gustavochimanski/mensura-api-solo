
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.services.service_mesas import MesaService
from app.api.cadastros.schemas.schema_mesa import (
    MesaResponse,
    MesaCreate,
    MesaUpdate,
    MesaStatusUpdate,
    MesaStatsResponse,
)
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db

router = APIRouter(
    prefix="/api/mesas/admin/mesas",
    tags=["Admin - Mesas"],
    dependencies=[Depends(get_current_user)]
)


def get_mesa_service(db: Session = Depends(get_db)) -> MesaService:
    """Dependency para obter o serviço de mesas."""
    return MesaService(db)


@router.get("/", response_model=List[dict])
def listar_mesas(
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Lista todas as mesas de uma empresa.
    
    Retorna lista de mesas com informações completas incluindo pedidos abertos.
    """
    return svc.listar_mesas(empresa_id=empresa_id)


@router.get("/search", response_model=List[dict])
def buscar_mesas(
    empresa_id: int = Query(..., description="ID da empresa"),
    q: Optional[str] = Query(None, description="Termo de busca (número/descrição)"),
    status: Optional[str] = Query(None, description="Filtrar por status: D, O ou R"),
    ativa: Optional[str] = Query(None, description="Filtrar por ativa: S ou N"),
    limit: int = Query(30, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Busca mesas com filtros opcionais.
    
    Permite filtrar por termo de busca, status e ativa.
    """
    return svc.buscar_mesas(
        empresa_id=empresa_id,
        q=q,
        status=status,
        ativa=ativa,
        limit=limit,
        offset=offset
    )


@router.get("/{mesa_id}", response_model=dict)
def obter_mesa(
    mesa_id: int,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Obtém uma mesa específica por ID.
    
    Retorna informações completas da mesa incluindo pedidos abertos.
    """
    return svc.obter_mesa(mesa_id=mesa_id, empresa_id=empresa_id)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def criar_mesa(
    data: MesaCreate,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Cria uma nova mesa.
    
    Requer código, descrição, capacidade, status e empresa_id.
    """
    if data.empresa_id != empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa_id do body deve corresponder ao empresa_id da query"
        )
    
    return svc.criar_mesa(data)


@router.put("/{mesa_id}", response_model=dict)
def atualizar_mesa(
    mesa_id: int,
    data: MesaUpdate,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Atualiza uma mesa existente.
    
    Todos os campos são opcionais. Apenas campos fornecidos serão atualizados.
    """
    return svc.atualizar_mesa(mesa_id=mesa_id, empresa_id=empresa_id, data=data)


@router.delete("/{mesa_id}", status_code=status.HTTP_200_OK)
def deletar_mesa(
    mesa_id: int,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Deleta uma mesa.
    
    Remove permanentemente a mesa do sistema.
    """
    return svc.deletar_mesa(mesa_id=mesa_id, empresa_id=empresa_id)


@router.patch("/{mesa_id}/status", response_model=dict)
def atualizar_status_mesa(
    mesa_id: int,
    data: MesaStatusUpdate,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Atualiza apenas o status da mesa.
    
    Status válidos: D (Disponível), O (Ocupada), R (Reservada).
    """
    return svc.atualizar_status(mesa_id=mesa_id, empresa_id=empresa_id, novo_status=data.status)


@router.post("/{mesa_id}/ocupar", response_model=dict)
def ocupar_mesa(
    mesa_id: int,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Ocupa uma mesa.
    
    Altera o status da mesa para "O" (Ocupada).
    """
    return svc.ocupar_mesa(mesa_id=mesa_id, empresa_id=empresa_id)


@router.post("/{mesa_id}/liberar", response_model=dict)
def liberar_mesa(
    mesa_id: int,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Libera uma mesa.
    
    Altera o status da mesa para "D" (Disponível) e limpa o cliente atual.
    """
    return svc.liberar_mesa(mesa_id=mesa_id, empresa_id=empresa_id)


@router.post("/{mesa_id}/reservar", response_model=dict)
def reservar_mesa(
    mesa_id: int,
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Reserva uma mesa.
    
    Altera o status da mesa para "R" (Reservada).
    """
    return svc.reservar_mesa(mesa_id=mesa_id, empresa_id=empresa_id)


@router.get("/stats", response_model=MesaStatsResponse)
def obter_stats_mesas(
    empresa_id: int = Query(..., description="ID da empresa"),
    svc: MesaService = Depends(get_mesa_service),
):
    """
    Obtém estatísticas das mesas de uma empresa.
    
    Retorna contagem total, disponíveis, ocupadas, reservadas e inativas.
    """
    stats = svc.obter_stats(empresa_id=empresa_id)
    return MesaStatsResponse(**stats)


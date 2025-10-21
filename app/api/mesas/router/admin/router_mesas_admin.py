from fastapi import (
    APIRouter, Depends, HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.mensura.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.mesas.repositories.repo_mesas import MesaRepository
from app.api.mesas.services.service_mesas import MesaService
from app.api.mesas.schemas.schema_mesa import (
    MesaIn, MesaOut, MesaUpdate, MesaSearchOut, MesaListOut, 
    MesaStatsOut, MesaStatusUpdate, StatusMesaEnum
)
from app.api.mesas.models.model_mesa import StatusMesa
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/mesas/admin/mesas",
    tags=["Admin - Mesas"],
    dependencies=[Depends(get_current_user)]
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

# -------- BUSCA --------
@router.get("/search", response_model=List[MesaSearchOut])
def search_mesas(
    q: Optional[str] = Query(None, description="Termo de busca por número/descrição"),
    status: Optional[StatusMesaEnum] = Query(None, description="Filtrar por status"),
    ativa: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Busca mesas com filtros"""
    service = MesaService(db)
    
    # Converte StatusMesaEnum para StatusMesa se necessário
    status_filter = StatusMesa(status.value) if status else None
    
    mesas = service.search(
        q=q, 
        status=status_filter, 
        ativa=ativa, 
        limit=limit, 
        offset=offset
    )
    
    return [
        MesaSearchOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            posicao_x=m.posicao_x,
            posicao_y=m.posicao_y,
            ativa=m.ativa
        )
        for m in mesas
    ]

# -------- LISTAR --------
@router.get("", response_model=List[MesaListOut])
def list_mesas(
    ativa: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    db: Session = Depends(get_db),
):
    """Lista todas as mesas"""
    service = MesaService(db)
    mesas = service.list_all(ativa)
    
    return [
        MesaListOut(
            id=m.id,
            numero=m.numero,
            descricao=m.descricao,
            capacidade=m.capacidade,
            status=StatusMesaEnum(m.status.value),
            status_descricao=m.status_descricao,
            status_cor=m.status_cor,
            ativa=m.ativa,
            label=m.label
        )
        for m in mesas
    ]

# -------- BUSCAR POR ID --------
@router.get("/{mesa_id}", response_model=MesaOut)
def get_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Busca mesa por ID"""
    service = MesaService(db)
    mesa = service.get_by_id(mesa_id)
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

# -------- CRIAR --------
@router.post(
    "",
    response_model=MesaOut,
    status_code=status.HTTP_201_CREATED
)
def criar_mesa(
    body: MesaIn,
    db: Session = Depends(get_db),
):
    """Cria uma nova mesa"""
    logger.info(f"[Mesas Admin] Criando mesa - numero={body.numero}")
    
    service = MesaService(db)
    try:
        mesa = service.create(body)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao criar mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao criar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao criar mesa: {str(e)}")
    
    logger.info(f"[Mesas Admin] Mesa criada com sucesso - id={mesa.id}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

# -------- ATUALIZAR --------
@router.put(
    "/{mesa_id}",
    response_model=MesaOut
)
def atualizar_mesa(
    mesa_id: int,
    body: MesaUpdate,
    db: Session = Depends(get_db),
):
    """Atualiza uma mesa"""
    logger.info(f"[Mesas Admin] Atualizando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.update(mesa_id, body)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao atualizar mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao atualizar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao atualizar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

# -------- ATUALIZAR STATUS --------
@router.patch(
    "/{mesa_id}/status",
    response_model=MesaOut
)
def atualizar_status_mesa(
    mesa_id: int,
    body: MesaStatusUpdate,
    db: Session = Depends(get_db),
):
    """Atualiza apenas o status da mesa"""
    logger.info(f"[Mesas Admin] Atualizando status da mesa - id={mesa_id}, status={body.status}")
    
    service = MesaService(db)
    try:
        mesa = service.update_status(mesa_id, body.status)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao atualizar status da mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao atualizar status da mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao atualizar status da mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

# -------- DELETAR --------
@router.delete(
    "/{mesa_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def deletar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Deleta uma mesa"""
    logger.info(f"[Mesas Admin] Deletando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        service.delete(mesa_id)
    except HTTPException as e:
        logger.error(f"[Mesas Admin] Erro ao deletar mesa: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro inesperado ao deletar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao deletar mesa: {str(e)}")
    
    logger.info(f"[Mesas Admin] Mesa deletada com sucesso - id={mesa_id}")
    return None

# -------- OPERAÇÕES DE STATUS --------
@router.post(
    "/{mesa_id}/ocupar",
    response_model=MesaOut
)
def ocupar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Ocupa uma mesa"""
    logger.info(f"[Mesas Admin] Ocupando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.ocupar_mesa_se_disponivel(mesa_id)
    except ValueError as e:
        logger.warning(f"[Mesas Admin] Mesa não pode ser ocupada: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao ocupar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao ocupar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

@router.post(
    "/{mesa_id}/liberar",
    response_model=MesaOut
)
def liberar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Libera uma mesa"""
    logger.info(f"[Mesas Admin] Liberando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.liberar_mesa_se_ocupada(mesa_id)
    except ValueError as e:
        logger.warning(f"[Mesas Admin] Mesa não pode ser liberada: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao liberar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao liberar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

@router.post(
    "/{mesa_id}/reservar",
    response_model=MesaOut
)
def reservar_mesa(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Reserva uma mesa"""
    logger.info(f"[Mesas Admin] Reservando mesa - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.reservar_mesa_se_disponivel(mesa_id)
    except ValueError as e:
        logger.warning(f"[Mesas Admin] Mesa não pode ser reservada: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao reservar mesa: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao reservar mesa: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

@router.post(
    "/{mesa_id}/marcar-livre",
    response_model=MesaOut
)
def marcar_mesa_livre(
    mesa_id: int = Path(..., title="ID da mesa"),
    db: Session = Depends(get_db),
):
    """Marca mesa como livre"""
    logger.info(f"[Mesas Admin] Marcando mesa como livre - id={mesa_id}")
    
    service = MesaService(db)
    try:
        mesa = service.marcar_livre(mesa_id)
    except Exception as e:
        logger.error(f"[Mesas Admin] Erro ao marcar mesa como livre: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao marcar mesa como livre: {str(e)}")
    
    return MesaOut(
        id=mesa.id,
        numero=mesa.numero,
        descricao=mesa.descricao,
        capacidade=mesa.capacidade,
        status=StatusMesaEnum(mesa.status.value),
        status_descricao=mesa.status_descricao,
        status_cor=mesa.status_cor,
        posicao_x=mesa.posicao_x,
        posicao_y=mesa.posicao_y,
        ativa=mesa.ativa,
        label=mesa.label,
        is_ocupada=mesa.is_ocupada,
        is_disponivel=mesa.is_disponivel,
        is_reservada=mesa.is_reservada,
        is_livre=mesa.is_livre
    )

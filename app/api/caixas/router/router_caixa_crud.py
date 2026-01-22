from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Path, Body
from sqlalchemy.orm import Session

from app.api.caixas.services.service_caixa_crud import CaixaCRUDService
from app.api.caixas.schemas.schema_caixa_crud import (
    CaixaCreate,
    CaixaUpdate,
    CaixaResponse
)
from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/caixa/admin/caixas",
    tags=["Admin - Caixas (CRUD)"],
    dependencies=[Depends(get_current_user)]
)

# ======================================================================
# ============================ CRUD CAIXAS =============================

@router.post("/", response_model=CaixaResponse, status_code=status.HTTP_201_CREATED)
def criar_caixa(
    data: CaixaCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Cria um novo caixa cadastrado.
    
    - **empresa_id**: ID da empresa (obrigatório)
    - **nome**: Nome/identificação do caixa (obrigatório)
    - **descricao**: Descrição opcional
    - **ativo**: Se o caixa está ativo (padrão: true)
    """
    logger.info(f"[Caixa] Criar caixa - empresa_id={data.empresa_id} usuario_id={current_user.id}")
    svc = CaixaCRUDService(db)
    return svc.create(data)

@router.get("/", response_model=List[CaixaResponse], status_code=status.HTTP_200_OK, operation_id="listar_caixas_cadastrados")
def listar_caixas(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa", gt=0),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros"),
    db: Session = Depends(get_db),
):
    """
    Lista caixas cadastrados com filtros opcionais.
    """
    svc = CaixaCRUDService(db)
    return svc.list(empresa_id=empresa_id, ativo=ativo, skip=skip, limit=limit)

@router.get("/{caixa_id}", response_model=CaixaResponse, status_code=status.HTTP_200_OK, operation_id="get_caixa_cadastrado")
def get_caixa(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    db: Session = Depends(get_db),
):
    """
    Busca um caixa específico por ID.
    """
    svc = CaixaCRUDService(db)
    return svc.get_by_id(caixa_id)

@router.put("/{caixa_id}", response_model=CaixaResponse, status_code=status.HTTP_200_OK)
def atualizar_caixa(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    data: CaixaUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Atualiza um caixa cadastrado.
    """
    logger.info(f"[Caixa] Atualizar caixa_id={caixa_id} usuario_id={current_user.id}")
    svc = CaixaCRUDService(db)
    return svc.update(caixa_id, data)

@router.delete("/{caixa_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_caixa(
    caixa_id: int = Path(..., description="ID do caixa", gt=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Remove um caixa (soft delete - marca como inativo).
    """
    logger.info(f"[Caixa] Deletar caixa_id={caixa_id} usuario_id={current_user.id}")
    svc = CaixaCRUDService(db)
    svc.delete(caixa_id)
    return None


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.mensura.repositories.categorias.vitrines_repo import VitrineRepository
from app.api.mensura.schemas.delivery.vitrine_schema import (
    CriarVitrineRequest, CriarVitrineResponse
)
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/vitrines/delivery",
    tags=["Delivery - vitrines"]
)


# ✅ GET vitrines com filtros opcionais
@router.get("", response_model=List[CriarVitrineResponse])
def listar_vitrines(
        empresa_id: int = Query(..., description="ID da empresa"),
        cod_categoria: Optional[int] = Query(None, description="Filtrar por ID da categoria"),
        db: Session = Depends(get_db)
):
    logger.info(f"[GET] Listando vitrines - empresa_id={empresa_id}, cod_categoria={cod_categoria}")
    repo = VitrineRepository(db)
    vitrines = repo.listar(cod_empresa=empresa_id, cod_categoria=cod_categoria)
    return [CriarVitrineResponse.from_orm(sub) for sub in vitrines]


# ✅ POST vitrines com validação e log
@router.post("", response_model=CriarVitrineResponse, status_code=status.HTTP_201_CREATED)
def criar_vitrines(
        request: CriarVitrineRequest,
        db: Session = Depends(get_db)
):
    logger.info(
        f"[POST] Criando vitrine - empresa={request.cod_empresa}, categoria={request.cod_categoria}, titulo={request.titulo}")

    repo = VitrineRepository(db)
    nova_sub = repo.create(request)
    return CriarVitrineResponse.model_validate(nova_sub)


# ✅ DELETE com tratamento de erro
@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_vitrine(
        sub_id: int,
        db: Session = Depends(get_db)
):
    logger.info(f"[DELETE] Deletando vitrines ID={sub_id}")

    repo = VitrineRepository(db)
    repo.delete(sub_id)
    return None

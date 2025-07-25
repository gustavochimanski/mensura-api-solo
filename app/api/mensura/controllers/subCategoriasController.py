from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.mensura.repositories.categorias.sub_categorias_repository import SubCategoriaRepository
from app.api.mensura.schemas.delivery.categorias.sub_categoria_schema import (
    CriarSubCategoriaRequest, CriarSubCategoriaResponse
)
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/subcategorias/delivery",
    tags=["Delivery - Subcategorias"]
)


# ✅ GET Subcategorias com filtros opcionais
@router.get("", response_model=List[CriarSubCategoriaResponse])
def listar_subcategorias(
        empresa_id: int = Query(..., description="ID da empresa"),
        cod_categoria: Optional[int] = Query(None, description="Filtrar por ID da categoria"),
        db: Session = Depends(get_db)
):
    logger.info(f"[GET] Listando subcategorias - empresa_id={empresa_id}, cod_categoria={cod_categoria}")
    repo = SubCategoriaRepository(db)
    subcategorias = repo.listar(cod_empresa=empresa_id, cod_categoria=cod_categoria)
    return [CriarSubCategoriaResponse.from_orm(sub) for sub in subcategorias]


# ✅ POST Subcategoria com validação e log
@router.post("", response_model=CriarSubCategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_subcategoria(
        request: CriarSubCategoriaRequest,
        db: Session = Depends(get_db)
):
    logger.info(
        f"[POST] Criando subcategoria - empresa={request.cod_empresa}, categoria={request.cod_categoria}, titulo={request.titulo}")

    repo = SubCategoriaRepository(db)
    nova_sub = repo.create(request)
    return CriarSubCategoriaResponse.model_validate(nova_sub)


# ✅ DELETE com tratamento de erro
@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_subcategoria(
        sub_id: int,
        db: Session = Depends(get_db)
):
    logger.info(f"[DELETE] Deletando subcategoria ID={sub_id}")

    repo = SubCategoriaRepository(db)
    repo.delete(sub_id)
    return None

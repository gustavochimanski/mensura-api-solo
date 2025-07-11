from fastapi import APIRouter, Depends, Query, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.mensura.repositories.categorias.sub_categorias_repository import SubCategoriaRepository
from app.api.mensura.schemas.delivery.categorias.sub_categoria_schema import CriarSubCategoriaRequest, CriarSubCategoriaResponse
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/subcategorias/delivery", tags=["Delivery - Subcategorias"])

@router.get("", response_model=List[CriarSubCategoriaResponse])
def listar_subcategorias(
    empresa_id: int = Query(..., description="ID da empresa"),
    cod_categoria: Optional[int] = Query(None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db)
):
    logger.info(f"Listando subcategorias da empresa {empresa_id} com filtro categoria={cod_categoria}")
    repo = SubCategoriaRepository(db)
    subs = repo.listar(cod_empresa=empresa_id, cod_categoria=cod_categoria)
    return [CriarSubCategoriaResponse.from_orm(s) for s in subs]


@router.post("", response_model=CriarSubCategoriaResponse, status_code=status.HTTP_201_CREATED)
async def criar_subcategoria(
    request: CriarSubCategoriaRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"Criando subcategoria: empresa={request.cod_empresa}, categoria={request.cod_categoria}, titulo={request.titulo}")
    repo = SubCategoriaRepository(db)
    sub_in = CriarSubCategoriaRequest(
        cod_empresa=request.cod_empresa,
        cod_categoria=request.cod_categoria,
        titulo=request.titulo,
        ordem=request.ordem
    )
    sub = repo.create(sub_in)
    return CriarSubCategoriaResponse.model_validate(sub)

@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_subcategoria(
    sub_id: int,
    db: Session = Depends(get_db)
):
    logger.info(f"Deletando subcategoria ID={sub_id}")
    repo = SubCategoriaRepository(db)
    repo.delete(sub_id)
    return None

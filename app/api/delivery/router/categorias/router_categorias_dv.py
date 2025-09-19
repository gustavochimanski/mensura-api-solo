from fastapi import (
    APIRouter, Depends, Form, File, UploadFile,
    HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.db_connection import get_db
from app.api.delivery.repositories.repo_categorias import CategoriaDeliveryRepository
from app.api.delivery.services.service_categoria import CategoriasService
from app.api.delivery.schemas.schema_categoria import (
    CategoriaDeliveryIn,
    CategoriaDeliveryOut, CategoriaSearchOut
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/cliente/categorias", tags=["Categorias - Cliente - Delivery"])

# -------- SEARCH --------
@router.get("/search", response_model=List[CategoriaSearchOut])
def search_categorias(
    q: Optional[str] = Query(None, description="Termo de busca por descrição/slug"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    cats = repos.search_all(q=q, limit=limit, offset=offset)
    return [
        CategoriaSearchOut(
            id=c.id,
            descricao=c.descricao,
            slug=c.slug,
            parent_id=c.parent_id,
            slug_pai=(c.parent.slug if c.parent else None),
            imagem=c.imagem,
        )
        for c in cats
    ]

# -------- GET BY ID -------
@router.get("/{cat_id}", response_model=CategoriaDeliveryOut)
def get_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"[Categorias] Get ID={cat_id}")
    c = repos.get_by_id(cat_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada")
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        slug=c.slug,
        parent_id=c.parent_id,
        slug_pai=c.parent.slug if c.parent else None,
        imagem=c.imagem,
        href=f"/categoria/{c.slug}",
        posicao=c.posicao,
    )

from fastapi import (
    APIRouter, Depends, Form, File, UploadFile,
    HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.delivery.repositories.repo_categorias_dv import CategoriaDeliveryRepository
from app.api.delivery.schemas.schema_categoria_dv import (
    CategoriaDeliveryIn,
    CategoriaDeliveryOut, CategoriaSearchOut
)
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/delivery/categorias", tags=["Delivery - Categorias"])

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

# -------- CRIAR --------
@router.post(
    "",
    response_model=CategoriaDeliveryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)]
)
def criar_categoria(
    body: CategoriaDeliveryIn,
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.create(body)
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

# -------- EDITAR --------
@router.put(
    "/{cat_id}",
    response_model=CategoriaDeliveryOut,
    dependencies=[Depends(get_current_user)]
)
def editar_categoria(
    cat_id: int,
    body: CategoriaDeliveryIn,
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.update(cat_id, body.model_dump(exclude_unset=True))
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

# -------- DELETAR --------
@router.delete(
    "/{cat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)]
)
def deletar_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    repos.delete(cat_id)
    logger.info(f"[Categorias] Deletada ID={cat_id}")
    return None

# -------- MOVER DIREITA --------
@router.post(
    "/{cat_id}/move-right",
    response_model=CategoriaDeliveryOut,
    dependencies=[Depends(get_current_user)]
)
def move_categoria_direita(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_right(cat_id)
    logger.info(f"[Categorias] Move right ID={cat_id}")
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

# -------- MOVER ESQUERDA --------
@router.post(
    "/{cat_id}/move-left",
    response_model=CategoriaDeliveryOut,
    dependencies=[Depends(get_current_user)]
)
def move_categoria_esquerda(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_left(cat_id)
    logger.info(f"[Categorias] Move left ID={cat_id}")
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

# -------- UPLOAD IMAGEM --------
@router.patch(
    "/{cat_id}/imagem",
    response_model=CategoriaDeliveryOut,
    dependencies=[Depends(get_current_user)]
)
async def upload_imagem_categoria(
    cat_id: int,
    cod_empresa: int = Form(...),
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    permitidos = {"image/jpeg", "image/png", "image/webp"}
    if imagem.content_type not in permitidos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de imagem inválido")
    try:
        url = upload_file_to_minio(db, cod_empresa, imagem, "categorias")
    except Exception:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao enviar imagem")

    repos = CategoriaDeliveryRepository(db)
    c = repos.update(cat_id, {"imagem": url})
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



@router.get("/search", response_model=List[CategoriaSearchOut])
def search_categorias(
    q: Optional[str] = Query(None, description="Termo de busca por descrição/slug"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    cats = repos.search_all(q=q, limit=limit, offset=offset)
    # map: parent.slug -> slug_pai
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
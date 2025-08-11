from fastapi import (
    APIRouter, Depends, Form, File, UploadFile,
    HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.db_connection import get_db
from app.api.delivery.repositories.categorias_dv_repo import CategoriaDeliveryRepository
from app.api.delivery.schemas.categoria_dv_schema import (
    CategoriaDeliveryIn,
    CategoriaDeliveryOut
)
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/api/delivery/categorias", tags=["Delivery - Categorias"])

@router.get("", response_model=List[CategoriaDeliveryOut])
def list_categorias(
    db: Session = Depends(get_db),
    parent_id: Optional[int] = Query(None, description="Filtra por pai (subcategorias)"),
):
    repos = CategoriaDeliveryRepository(db)
    if parent_id is not None:
        logger.info(f"[Categorias] Listando por parent_id={parent_id}")
        cats = repos.list_by_parent(parent_id)
    else:
        logger.info("[Categorias] Listando todas")
        cats = repos.list_all()
    return [
        CategoriaDeliveryOut(
            id=c.id,
            label=c.descricao,  # derivado
            slug=c.slug,
            parent_id=c.parent_id,
            slug_pai=c.parent.slug if c.parent else None,
            imagem=c.imagem,
            href=f"/categoria/{c.slug}",  # derivado
            posicao=c.posicao,
            is_home=c.is_home,  # property no model
        )
        for c in cats
    ]


@router.get("/{cat_id}", response_model=CategoriaDeliveryOut)
def get_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"[Categorias] Get ID={cat_id}")
    c = repos.get_by_id(cat_id)
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        slug=c.slug,
        parent_id=c.parent_id,
        slug_pai=c.parent.slug if c.parent else None,
        imagem=c.imagem,
        href=f"/categoria/{c.slug}",
        posicao=c.posicao,
        is_home=c.is_home,
    )


@router.post("", response_model=CategoriaDeliveryOut, status_code=status.HTTP_201_CREATED)
def criar_categoria(body: CategoriaDeliveryIn, db: Session = Depends(get_db)):
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
        is_home=c.is_home,
    )

@router.put("/{cat_id}", response_model=CategoriaDeliveryOut)
def editar_categoria(cat_id: int, body: CategoriaDeliveryIn, db: Session = Depends(get_db)):
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
        is_home=c.is_home,
    )


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    repos.delete(cat_id)
    logger.info(f"[Categorias] Deletada ID={cat_id}")
    return None

@router.post("/{cat_id}/move-right", response_model=CategoriaDeliveryOut)
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
        is_home=c.is_home,
    )


@router.post("/{cat_id}/move-left", response_model=CategoriaDeliveryOut)
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
        is_home=c.is_home,
    )


@router.post("/{cat_id}/toggle-home", response_model=CategoriaDeliveryOut)
def toggle_home(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    """
    Alterna `tipo_exibicao` para exibir na Home (valor 'P') ou remover.
    """
    repos = CategoriaDeliveryRepository(db)
    c = repos.toggle_home(cat_id, on=True)
    logger.info(f"[Categorias] Toggle home ID={cat_id}")
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        slug=c.slug,
        parent_id=c.parent_id,
        slug_pai=c.parent.slug if c.parent else None,
        imagem=c.imagem,
        href=f"/categoria/{c.slug}",
        posicao=c.posicao,
        is_home=c.is_home,
    )

@router.patch("/{cat_id}/imagem", response_model=CategoriaDeliveryOut)
async def upload_imagem_categoria(
    cat_id: int,
    cod_empresa: int,
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
        is_home=bool(c.is_home),
    )

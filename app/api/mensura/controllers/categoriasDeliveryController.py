# app/api/mensura/controllers/categoriasDeliveryController.py
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.db_connection import get_db
from app.api.mensura.repositories.delivery.categorias_dv_repo import (
    CategoriaDeliveryRepository
)
from app.api.mensura.schemas.delivery.categoria_dv_schema import (
    CategoriaDeliveryIn,
    CategoriaDeliveryOut
)
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/categorias/delivery", tags=["Delivery - Categorias"])


@router.get("", response_model=List[CategoriaDeliveryOut])
def list_categorias(db: Session = Depends(get_db)):
    repos = CategoriaDeliveryRepository(db)
    logger.info("Listando todas as categorias de delivery")
    cats = repos.list_all()
    return [
        CategoriaDeliveryOut(
            id=c.id,
            label=c.descricao,
            imagem=c.imagem,
            slug=c.slug,
            slug_pai=c.slug_pai,
            href=c.href,
            posicao=c.posicao,
        )
        for c in cats
    ]

@router.get("/{cat_id}", response_model=CategoriaDeliveryOut)
def get_categoria(cat_id: int, db: Session = Depends(get_db)):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"Buscando categoria ID={cat_id}")
    c = repos.get_by_id(cat_id)
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        imagem=c.imagem,
        slug=c.slug,
        slug_pai=c.slug_pai,
        href=c.href,
        posicao=c.posicao,
    )


@router.post("", response_model=CategoriaDeliveryOut, status_code=status.HTTP_201_CREATED)
async def criar_categoria(
    cod_empresa: int = Form(...),
    descricao: str = Form(...),
    slug: str = Form(...),
    slug_pai: Optional[str] = Form(None),
    posicao: Optional[int] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"Criando categoria: {descricao}")
    imagem_url = None

    if imagem:
        permitidos = {"image/jpeg", "image/png", "image/webp"}
        if imagem.content_type not in permitidos:
            raise HTTPException(400, "Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(db, cod_empresa, imagem, "categorias")
        except RuntimeError as e:
            logger.error(f"Upload falhou: {e}")
            raise HTTPException(500, "Erro ao enviar imagem")

    cat_in = CategoriaDeliveryIn(
        descricao=descricao,
        slug=slug,
        slug_pai=slug_pai,
        imagem=imagem_url,
        posicao=posicao,
    )
    c = repos.create(cat_in)
    logger.info(f"Categoria criada com ID={c.id}")
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        imagem=c.imagem,
        slug=c.slug,
        slug_pai=c.slug_pai,
        href=c.href,
        posicao=c.posicao,
    )


@router.put("/{cat_id}", response_model=CategoriaDeliveryOut)
async def editar_categoria(
    cat_id: int,
    descricao: str = Form(...),
    slug: str = Form(...),
    slug_pai: Optional[str] = Form(None),
    posicao: Optional[int] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"Editando categoria ID={cat_id}")
    imagem_url = None

    if imagem:
        permitidos = {"image/jpeg", "image/png", "image/webp"}
        if imagem.content_type not in permitidos:
            raise HTTPException(400, "Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(imagem, slug, bucket="categorias")
        except RuntimeError as e:
            logger.error(f"Upload falhou: {e}")
            raise HTTPException(500, "Erro ao enviar imagem")

    updates = {
        "descricao": descricao,
        "slug": slug,
        "slug_pai": slug_pai,
        "posicao": posicao,
        "imagem": imagem_url,
    }
    c = repos.update(cat_id, updates)
    logger.info(f"Categoria ID={cat_id} atualizada")
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        imagem=c.imagem,
        slug=c.slug,
        slug_pai=c.slug_pai,
        href=c.href,
        posicao=c.posicao,
    )


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(cat_id: int, db: Session = Depends(get_db)):
    repos = CategoriaDeliveryRepository(db)
    repos.delete(cat_id)
    logger.info(f"Categoria ID={cat_id} deletada")
    return None


@router.post("/{cat_id}/move-right", response_model=CategoriaDeliveryOut)
def move_categoria_direita(cat_id: int, db: Session = Depends(get_db)):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_right(cat_id)
    logger.info(f"Categoria ID={cat_id} movida para direita")
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        imagem=c.imagem,
        slug=c.slug,
        slug_pai=c.slug_pai,
        href=c.href,
        posicao=c.posicao,
    )


@router.post("/{cat_id}/move-left", response_model=CategoriaDeliveryOut)
def move_categoria_esquerda(cat_id: int, db: Session = Depends(get_db)):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_left(cat_id)
    logger.info(f"Categoria ID={cat_id} movida para esquerda")
    return CategoriaDeliveryOut(
        id=c.id,
        label=c.descricao,
        imagem=c.imagem,
        slug=c.slug,
        slug_pai=c.slug_pai,
        href=c.href,
        posicao=c.posicao,
    )

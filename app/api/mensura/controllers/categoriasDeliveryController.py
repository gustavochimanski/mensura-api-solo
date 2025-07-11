# app/api/mensura/controllers/categoriasDeliveryController.py
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.db_connection import get_db
from app.api.mensura.repositories.categorias.categoriasDeliveryRepository import CategoriaDeliveryRepository
from app.api.mensura.schemas.delivery.categorias.categoria_schema import (
    CategoriaDeliveryIn,
    CategoriaDeliveryOut
)
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio

router = APIRouter(prefix="/categorias/delivery", tags=["Delivery - Categorias"])

@router.get("", response_model=List[CategoriaDeliveryOut])
def listar_categorias(db: Session = Depends(get_db)):
    logger.info("Listando categorias de delivery...")
    repositorio = CategoriaDeliveryRepository(db)
    categorias = repositorio.listar()
    logger.info(f"{len(categorias)} categorias encontradas")

    return [
        CategoriaDeliveryOut(
            id=cat.id,
            label=cat.descricao,
            imagem=cat.imagem,
            slug=cat.slug,
            slug_pai=cat.slug_pai,
            href=cat.href,
            posicao=cat.posicao   # ⬅️ mapeando
        )
        for cat in categorias
    ]

@router.post("", response_model=CategoriaDeliveryOut, status_code=status.HTTP_201_CREATED)
async def criar_categoria(
    descricao: str = Form(...),
    slug: str = Form(...),
    slug_pai: Optional[str] = Form(None),
    posicao: Optional[int] = Form(None),             # ⬅️ recebendo do formulário
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    logger.info(f"Criando categoria: descricao={descricao}, slug={slug}, slug_pai={slug_pai}, posicao={posicao}")
    imagem_url = None

    if imagem:
        permitidos = {"image/jpeg", "image/png", "image/webp"}
        if imagem.content_type not in permitidos:
            logger.warning(f"Formato inválido: {imagem.content_type}")
            raise HTTPException(400, "Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(file=imagem, slug=slug, bucket="categorias")
        except RuntimeError as e:
            logger.error(f"Falha no upload: {e}")
            raise HTTPException(500, "Erro ao enviar imagem")

    repositorio = CategoriaDeliveryRepository(db)
    try:
        cat_in = CategoriaDeliveryIn(
            descricao=descricao,
            slug=slug,
            slug_pai=slug_pai,
            imagem=imagem_url,
            posicao=posicao             # ⬅️ passando para o schema de input
        )
        cat = repositorio.create(cat_in)
        logger.info(f"Categoria criada com ID={cat.id}")
    except Exception as e:
        logger.error(f"Erro ao criar categoria: {e}")
        raise HTTPException(500, "Erro ao criar categoria")

    return CategoriaDeliveryOut(
        id=cat.id,
        label=cat.descricao,
        imagem=cat.imagem,
        slug=cat.slug,
        slug_pai=cat.slug_pai,
        href=cat.href,
        posicao=cat.posicao         # ⬅️ retornando no output
    )

@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(cat_id: int, db: Session = Depends(get_db)):
    logger.info(f"Deletando categoria ID={cat_id}")
    repositorio = CategoriaDeliveryRepository(db)
    repositorio.delete(cat_id)
    return None

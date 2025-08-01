# app/api/mensura/controllers/categorias_dv_controller.py
from fastapi import (
    APIRouter, Depends, Form, File, UploadFile,
    HTTPException, status, Path
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

router = APIRouter(prefix="/categorias/delivery", tags=["Delivery - Categorias"])


@router.get("", response_model=List[CategoriaDeliveryOut])
def list_categorias(db: Session = Depends(get_db)):
    repos = CategoriaDeliveryRepository(db)
    logger.info("Listando todas as categorias de delivery")
    cats = repos.list_all()
    return [CategoriaDeliveryOut.from_orm(c) for c in cats]


@router.get("/{cat_id}", response_model=CategoriaDeliveryOut)
def get_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"Buscando categoria ID={cat_id}")
    c = repos.get_by_id(cat_id)
    return CategoriaDeliveryOut.from_orm(c)


@router.post("", response_model=CategoriaDeliveryOut, status_code=status.HTTP_201_CREATED)
async def criar_categoria(
    cod_empresa: int = Form(...),
    descricao: str = Form(...),
    slug: str = Form(...),
    parent_id: Optional[int] = Form(None),
    posicao: Optional[int] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"Criando categoria: {descricao}")
    imagem_url: Optional[str] = None

    # upload de imagem (se houver)
    if imagem:
        permitidos = {"image/jpeg", "image/png", "image/webp"}
        if imagem.content_type not in permitidos:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(db, cod_empresa, imagem, "categorias")
        except Exception as e:
            logger.error("Upload falhou", exc_info=True)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao enviar imagem")

    cat_in = CategoriaDeliveryIn(
        descricao=descricao,
        slug=slug,
        parent_id=parent_id,
        imagem=imagem_url,
        posicao=posicao,
    )

    # *** Wrap para debugar o 500 ***
    try:
        c = repos.create(cat_in)
    except HTTPException:
        # se for um HTTPException lançado no repositório, repassa
        raise
    except Exception as e:
        # captura QUALQUER outro erro, log completo de stacktrace e retorna 500 genérico
        logger.error("Erro ao criar categoria no repositório", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar categoria"
        )

    logger.info(f"Categoria criada com ID={c.id}")
    return CategoriaDeliveryOut.from_orm(c)

@router.put("/{cat_id}", response_model=CategoriaDeliveryOut)
async def editar_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    cod_empresa: int = Form(...),
    descricao: str = Form(...),
    slug: str = Form(...),
    parent_id: Optional[int] = Form(None),
    posicao: Optional[int] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"Editando categoria ID={cat_id}")
    imagem_url: Optional[str] = None

    if imagem:
        permitidos = {"image/jpeg", "image/png", "image/webp"}
        if imagem.content_type not in permitidos:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de imagem inválido")
        try:
            imagem_url = upload_file_to_minio(db, cod_empresa, imagem, "categorias")
        except Exception as e:
            logger.error(f"Upload falhou: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao enviar imagem")

    updates = {
        "descricao": descricao,
        "slug": slug,
        "parent_id": parent_id,
        "posicao": posicao,
        "imagem": imagem_url,
    }
    c = repos.update(cat_id, updates)
    logger.info(f"Categoria ID={cat_id} atualizada")
    return CategoriaDeliveryOut.from_orm(c)


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    repos.delete(cat_id)
    logger.info(f"Categoria ID={cat_id} deletada")
    return None


@router.post("/{cat_id}/move-right", response_model=CategoriaDeliveryOut)
def move_categoria_direita(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_right(cat_id)
    logger.info(f"Categoria ID={cat_id} movida para direita")
    return CategoriaDeliveryOut.from_orm(c)


@router.post("/{cat_id}/move-left", response_model=CategoriaDeliveryOut)
def move_categoria_esquerda(
    cat_id: int = Path(..., title="ID da categoria"),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_left(cat_id)
    logger.info(f"Categoria ID={cat_id} movida para esquerda")
    return CategoriaDeliveryOut.from_orm(c)

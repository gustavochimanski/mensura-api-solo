from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.cadastros.schemas.schema_categoria import (
    CategoriaDeliveryAdminIn,
    CategoriaDeliveryAdminUpdate,
    CategoriaDeliveryIn,
    CategoriaDeliveryOut,
    CategoriaSearchOut,
)
from app.api.cadastros.repositories.repo_categoria import CategoriaDeliveryRepository
from app.api.cardapio.repositories.repo_categorias_dv import CategoriaDeliveryDVRepository
from app.api.cardapio.services.service_categoria_dv import CategoriasService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/cardapio/admin/categorias",
    tags=["Admin - Cardapio - Categorias"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=List[CategoriaDeliveryOut])
def listar_categorias(
    parent_id: Optional[int] = Query(
        None,
        description="Quando informado, retorna apenas as categorias filhas do ID informado.",
    ),
    db: Session = Depends(get_db),
):
    repo = CategoriaDeliveryDVRepository(db)
    categorias = repo.list_by_parent(parent_id)
    return [CategoriaDeliveryOut.model_validate(cat, from_attributes=True) for cat in categorias]


@router.get("/search", response_model=List[CategoriaSearchOut])
def buscar_categorias(
    q: Optional[str] = Query(None, description="Termo de busca por descrição ou slug."),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    repo = CategoriaDeliveryDVRepository(db)
    categorias = repo.search_all(q, limit=limit, offset=offset)
    return [CategoriaSearchOut.model_validate(cat, from_attributes=True) for cat in categorias]


@router.get("/{categoria_id}", response_model=CategoriaDeliveryOut)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
):
    repo = CategoriaDeliveryDVRepository(db)
    categoria = repo.get_by_id(categoria_id)
    if not categoria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    return CategoriaDeliveryOut.model_validate(categoria, from_attributes=True)


@router.post("/", response_model=CategoriaDeliveryOut, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    payload: CategoriaDeliveryAdminIn,
    db: Session = Depends(get_db),
):
    logger.info(
        "[Categorias Delivery][Admin] Criando categoria - empresa=%s descricao=%s parent_id=%s",
        payload.cod_empresa,
        payload.descricao,
        payload.parent_id,
    )

    repo = CategoriaDeliveryRepository(db)
    categoria = repo.create(
        CategoriaDeliveryIn(**payload.model_dump(exclude={"cod_empresa"}))
    )
    return CategoriaDeliveryOut.model_validate(categoria, from_attributes=True)


@router.put("/{categoria_id}", response_model=CategoriaDeliveryOut)
def atualizar_categoria(
    categoria_id: int,
    payload: CategoriaDeliveryAdminUpdate,
    db: Session = Depends(get_db),
):
    logger.info(
        "[Categorias Delivery][Admin] Atualizando categoria - empresa=%s categoria_id=%s",
        payload.cod_empresa,
        categoria_id,
    )

    service = CategoriasService(db)
    dados_atualizados = payload.model_dump(
        exclude={"cod_empresa"}, exclude_unset=True, exclude_none=True
    )
    categoria = service.update(
        categoria_id,
        dados_atualizados,
        cod_empresa=payload.cod_empresa,
    )
    return CategoriaDeliveryOut.model_validate(categoria, from_attributes=True)


@router.patch("/{categoria_id}/imagem", response_model=CategoriaDeliveryOut)
async def atualizar_imagem_categoria(
    categoria_id: int,
    cod_empresa: int = Form(...),
    imagem: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    logger.info(
        "[Categorias Delivery][Admin] Atualizando imagem da categoria - empresa=%s categoria_id=%s",
        cod_empresa,
        categoria_id,
    )

    if imagem.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de imagem inválido. Use JPEG, PNG ou WEBP.",
        )

    service = CategoriasService(db)
    categoria = service.update(
        categoria_id,
        {},
        cod_empresa=cod_empresa,
        file=imagem,
    )
    return CategoriaDeliveryOut.model_validate(categoria, from_attributes=True)


@router.post("/{categoria_id}/move-left", response_model=CategoriaDeliveryOut)
def mover_categoria_para_esquerda(
    categoria_id: int,
    db: Session = Depends(get_db),
):
    logger.info(
        "[Categorias Delivery][Admin] Movendo categoria para a esquerda - categoria_id=%s",
        categoria_id,
    )

    service = CategoriasService(db)
    categoria = service.move_left(categoria_id)
    return CategoriaDeliveryOut.model_validate(categoria, from_attributes=True)


@router.post("/{categoria_id}/move-right", response_model=CategoriaDeliveryOut)
def mover_categoria_para_direita(
    categoria_id: int,
    db: Session = Depends(get_db),
):
    logger.info(
        "[Categorias Delivery][Admin] Movendo categoria para a direita - categoria_id=%s",
        categoria_id,
    )

    service = CategoriasService(db)
    categoria = service.move_right(categoria_id)
    return CategoriaDeliveryOut.model_validate(categoria, from_attributes=True)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    categoria_id: int,
    cod_empresa: Optional[int] = Query(
        None,
        description="Identificador da empresa proprietária da categoria. Quando informado, remove também a imagem associada.",
    ),
    db: Session = Depends(get_db),
):
    logger.info(
        "[Categorias Delivery][Admin] Deletando categoria - empresa=%s categoria_id=%s",
        cod_empresa,
        categoria_id,
    )

    service = CategoriasService(db)
    service.delete(categoria_id, cod_empresa)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


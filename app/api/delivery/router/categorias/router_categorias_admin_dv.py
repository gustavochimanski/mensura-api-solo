from fastapi import (
    APIRouter, Depends, Form, File, UploadFile,
    HTTPException, status, Path, Query
)
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.mensura.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.delivery.repositories.repo_categorias import CategoriaDeliveryRepository
from app.api.delivery.services.service_categoria import CategoriasService
from app.api.delivery.schemas.schema_categoria import (
    CategoriaDeliveryIn,
    CategoriaDeliveryOut, CategoriaSearchOut
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/categorias/admin", tags=["Admin", "Delivery","Categorias"])

# -------- SEARCH --------
@router.get("/search", response_model=List[CategoriaSearchOut])
def search_categorias(
    q: Optional[str] = Query(None, description="Termo de busca por descrição/slug"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    logger.info(f"[Categorias Admin] Get ID={cat_id}")
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"[Categorias Admin] Criando categoria - descricao={body.descricao}, imagem={body.imagem}, parent_id={body.parent_id}")
    
    # Valida se parent_id existe (se fornecido)
    if body.parent_id:
        repos = CategoriaDeliveryRepository(db)
        try:
            parent = repos.get_by_id(body.parent_id)
            logger.info(f"[Categorias Admin] Categoria pai encontrada - id={parent.id}, descricao={parent.descricao}")
        except HTTPException as e:
            logger.error(f"[Categorias Admin] Categoria pai não encontrada - id={body.parent_id}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Categoria pai não encontrada: {body.parent_id}")
    
    repos = CategoriaDeliveryRepository(db)
    try:
        c = repos.create(body)
    except HTTPException as e:
        logger.error(f"[Categorias Admin] Erro ao criar categoria: {e}")
        raise e
    except Exception as e:
        logger.error(f"[Categorias Admin] Erro inesperado ao criar categoria: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao criar categoria: {str(e)}")
    
    logger.info(f"[Categorias Admin] Categoria criada com sucesso - id={c.id}, imagem={c.imagem}")
    
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CategoriasService(db)
    c = service.update(cat_id, body.model_dump(exclude_unset=True))
    if not c:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Falha ao atualizar categoria")
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CategoriasService(db)
    service.delete(cat_id, cod_empresa=1)  # TODO: pegar cod_empresa do usuário logado
    logger.info(f"[Categorias Admin] Deletada ID={cat_id}")
    return None

# -------- MOVER DIREITA --------
@router.post(
    "/{cat_id}/move-right",
    response_model=CategoriaDeliveryOut,
    dependencies=[Depends(get_current_user)]
)
def move_categoria_direita(
    cat_id: int = Path(..., title="ID da categoria"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_right(cat_id)
    logger.info(f"[Categorias Admin] Move right ID={cat_id}")
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repos = CategoriaDeliveryRepository(db)
    c = repos.move_left(cat_id)
    logger.info(f"[Categorias Admin] Move left ID={cat_id}")
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"[Categorias Admin] Upload imagem - categoria_id={cat_id}, empresa_id={cod_empresa}")
    
    # Valida se a empresa existe
    from app.api.mensura.repositories.empresa_repo import EmpresaRepository
    empresa_repo = EmpresaRepository(db)
    empresa = empresa_repo.get_empresa_by_id(cod_empresa)
    if not empresa:
        logger.error(f"[Categorias Admin] Empresa não encontrada - id={cod_empresa}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")
    
    # Valida se a categoria existe
    repos = CategoriaDeliveryRepository(db)
    try:
        categoria = repos.get_by_id(cat_id)
        logger.info(f"[Categorias Admin] Categoria encontrada - id={categoria.id}, descricao={categoria.descricao}")
    except HTTPException as e:
        logger.error(f"[Categorias Admin] Categoria não encontrada - id={cat_id}")
        raise e
    
    permitidos = {"image/jpeg", "image/png", "image/webp"}
    if imagem.content_type not in permitidos:
        logger.warning(f"[Categorias Admin] Formato de imagem inválido: {imagem.content_type}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de imagem inválido")
    
    try:
        service = CategoriasService(db)
        c = service.update(cat_id, {}, cod_empresa, imagem)
        logger.info(f"[Categorias Admin] Categoria atualizada com imagem: {c.id}")
    except ValueError as e:
        logger.error(f"[Categorias Admin] Erro de validação no upload: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        logger.error(f"[Categorias Admin] Erro inesperado no upload: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao enviar imagem: {str(e)}")
    
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

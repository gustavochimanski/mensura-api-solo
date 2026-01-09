from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.core.admin_dependencies import get_current_user
from app.api.cadastros.services.service_categorias import CategoriaService
from app.api.cadastros.schemas.schema_categorias import (
    CriarCategoriaRequest,
    AtualizarCategoriaRequest,
    CategoriaResponse,
    CategoriasPaginadasResponse,
    CategoriaArvoreResponse,
    CategoriaListItem
)

router = APIRouter(prefix="/api/cadastros/admin/categorias", tags=["Admin - Cadastros - Categorias"], dependencies=[Depends(get_current_user)])


@router.post("/", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    request: CriarCategoriaRequest,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova categoria.
    
    - **descricao**: Descrição da categoria (obrigatório)
    - **parent_id**: ID da categoria pai para subcategorias (opcional)
    - **ativo**: Status ativo/inativo da categoria (padrão: True)
    """
    service = CategoriaService(db)
    return service.criar_categoria(request)


@router.get("/{categoria_id}", response_model=CategoriaResponse)
def buscar_categoria_por_id(
    categoria_id: int,
    db: Session = Depends(get_db)
):
    """
    Busca uma categoria específica por ID.
    """
    service = CategoriaService(db)
    return service.buscar_categoria_por_id(categoria_id)


@router.get("/", response_model=CategoriasPaginadasResponse)
def listar_categorias_paginado(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    apenas_ativas: bool = Query(True, description="Filtrar apenas categorias ativas"),
    parent_id: Optional[int] = Query(None, description="Filtrar por categoria pai"),
    db: Session = Depends(get_db)
):
    """
    Lista categorias com paginação.
    
    - **page**: Número da página (padrão: 1)
    - **limit**: Itens por página (padrão: 10, máximo: 100)
    - **apenas_ativas**: Filtrar apenas categorias ativas (padrão: True)
    - **parent_id**: Filtrar por categoria pai (opcional)
    """
    service = CategoriaService(db)
    return service.listar_categorias_paginado(page, limit, apenas_ativas, parent_id)


@router.put("/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    request: AtualizarCategoriaRequest,
    db: Session = Depends(get_db)
):
    """
    Atualiza uma categoria existente.
    
    - **descricao**: Nova descrição da categoria (opcional)
    - **parent_id**: Novo ID da categoria pai (opcional)
    - **ativo**: Novo status ativo/inativo (opcional)
    """
    service = CategoriaService(db)
    return service.atualizar_categoria(categoria_id, request)


@router.delete("/{categoria_id}")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db)
):
    """
    Deleta uma categoria (soft delete).
    
    **Nota**: Só é possível deletar categorias que não possuem subcategorias ativas.
    """
    service = CategoriaService(db)
    return service.deletar_categoria(categoria_id)


@router.get("/buscar/termo", response_model=CategoriasPaginadasResponse)
def buscar_categorias_por_termo(
    termo: str = Query(..., min_length=1, description="Termo de busca"),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    apenas_ativas: bool = Query(True, description="Filtrar apenas categorias ativas"),
    db: Session = Depends(get_db)
):
    """
    Busca categorias por termo de pesquisa.
    
    - **termo**: Termo para buscar na descrição das categorias
    - **page**: Número da página (padrão: 1)
    - **limit**: Itens por página (padrão: 10, máximo: 100)
    - **apenas_ativas**: Filtrar apenas categorias ativas (padrão: True)
    """
    service = CategoriaService(db)
    return service.buscar_categorias_por_termo(termo, page, limit, apenas_ativas)


@router.get("/arvore/estrutura", response_model=CategoriaArvoreResponse)
def buscar_arvore_categorias(
    apenas_ativas: bool = Query(True, description="Filtrar apenas categorias ativas"),
    db: Session = Depends(get_db)
):
    """
    Busca todas as categorias organizadas em estrutura de árvore.
    
    - **apenas_ativas**: Filtrar apenas categorias ativas (padrão: True)
    """
    service = CategoriaService(db)
    return service.buscar_arvore_categorias(apenas_ativas)


@router.get("/raiz/lista", response_model=List[CategoriaListItem])
def buscar_categorias_raiz(
    apenas_ativas: bool = Query(True, description="Filtrar apenas categorias ativas"),
    db: Session = Depends(get_db)
):
    """
    Busca apenas categorias raiz (sem categoria pai).
    
    - **apenas_ativas**: Filtrar apenas categorias ativas (padrão: True)
    """
    service = CategoriaService(db)
    return service.buscar_categorias_raiz(apenas_ativas)


@router.get("/{parent_id}/filhos", response_model=List[CategoriaListItem])
def buscar_filhos_da_categoria(
    parent_id: int,
    apenas_ativas: bool = Query(True, description="Filtrar apenas categorias ativas"),
    db: Session = Depends(get_db)
):
    """
    Busca filhos de uma categoria específica.
    
    - **parent_id**: ID da categoria pai
    - **apenas_ativas**: Filtrar apenas categorias ativas (padrão: True)
    """
    service = CategoriaService(db)
    return service.buscar_filhos_da_categoria(parent_id, apenas_ativas)

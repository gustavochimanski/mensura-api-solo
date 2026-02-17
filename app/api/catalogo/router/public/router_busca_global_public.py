"""
Router público para busca global de produtos, receitas e combos (sem autenticação)
"""
from fastapi import APIRouter, Query, status
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.catalogo.services.service_busca_global import BuscaGlobalService
from app.api.catalogo.schemas.schema_busca_global import BuscaGlobalResponse


router = APIRouter(
    prefix="/api/catalogo/public/busca",
    tags=["Public - Catalogo - Busca Global"],
)


@router.get(
    "/global",
    response_model=BuscaGlobalResponse,
    status_code=status.HTTP_200_OK,
    summary="Busca global pública de produtos, receitas e combos",
    description="""
    Realiza uma busca global em produtos, receitas e combos de uma empresa.
    Endpoint público — não requer token.
    
    **Busca em:**
    - **Produtos**: Busca por descrição ou código de barras
    - **Receitas**: Busca por nome ou descrição
    - **Combos**: Busca por título ou descrição
    
    **Filtros:**
    - `empresa_id`: ID da empresa (obrigatório)
    - `termo`: Termo de busca (opcional - se vazio, retorna primeiros itens)
    - `apenas_disponiveis`: Filtrar apenas itens disponíveis (padrão: true)
    - `apenas_ativos`: Filtrar apenas itens ativos (padrão: true)
    - `limit`: Limite de resultados por tipo (padrão: 50, máximo: 200)
    - `page`: Número da página para paginação (padrão: 1, mínimo: 1)
    
    **Retorno:**
    - `produtos`: Lista de produtos encontrados
    - `receitas`: Lista de receitas encontradas
    - `combos`: Lista de combos encontrados
    - `quantidade_produtos`: Quantidade total de itens retornados (produtos + receitas + combos)
    - `total`: Total de resultados encontrados (legado)
    """,
    responses={
        200: {"description": "Busca realizada com sucesso"},
        400: {"description": "Parâmetros inválidos"},
    },
)
def buscar_global_public(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    termo: str = Query("", description="Termo de busca (opcional - se vazio, retorna primeiros itens)"),
    apenas_disponiveis: bool = Query(
        True,
        description="Filtrar apenas itens disponíveis (produtos/receitas)"
    ),
    apenas_ativos: bool = Query(
        True,
        description="Filtrar apenas itens ativos"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Limite de resultados por tipo"
    ),
    page: int = Query(
        1,
        ge=1,
        description="Número da página para paginação"
    ),
    db: Session = Depends(get_db),
):
    """
    Busca global pública em produtos, receitas e combos.
    """
    service = BuscaGlobalService(db)
    return service.buscar(
        empresa_id=empresa_id,
        termo=termo,
        apenas_disponiveis=apenas_disponiveis,
        apenas_ativos=apenas_ativos,
        limit=limit,
        page=page,
    )


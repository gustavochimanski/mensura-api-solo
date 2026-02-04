"""
Router para busca global de produtos, receitas e combos (Cliente)
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.api.catalogo.services.service_busca_global import BuscaGlobalService
from app.api.catalogo.schemas.schema_busca_global import BuscaGlobalResponse
from app.api.cadastros.models.model_cliente_dv import ClienteModel


router = APIRouter(
    prefix="/api/catalogo/client/busca",
    tags=["Client - Catalogo - Busca Global"],
)


@router.get(
    "/global",
    response_model=BuscaGlobalResponse,
    status_code=status.HTTP_200_OK,
    summary="Busca global de produtos, receitas e combos (Cliente)",
    description="""
    Realiza uma busca global em produtos, receitas e combos de uma empresa.
    Disponível para clientes autenticados.
    
    **Busca em:**
    - **Produtos**: Busca por descrição ou código de barras
    - **Receitas**: Busca por nome ou descrição
    - **Combos**: Busca por título ou descrição
    
    **Filtros:**
    - `empresa_id`: ID da empresa (obrigatório)
    - `termo`: Termo de busca (obrigatório)
    - `apenas_disponiveis`: Filtrar apenas itens disponíveis (padrão: true)
    - `apenas_ativos`: Filtrar apenas itens ativos (padrão: true)
    - `limit`: Limite de resultados por tipo (padrão: 50, máximo: 200)
    
    **Retorno:**
    - `produtos`: Lista de produtos encontrados
    - `receitas`: Lista de receitas encontradas
    - `combos`: Lista de combos encontrados
    - `quantidade_produtos`: Quantidade total de itens retornados (produtos + receitas + combos)
    - `total`: Total de resultados encontrados (legado)
    
    **Autenticação:** Requer header `X-Super-Token` com o token do cliente.
    """,
    responses={
        200: {"description": "Busca realizada com sucesso"},
        400: {"description": "Parâmetros inválidos"},
        401: {"description": "Não autenticado"},
    },
)
def buscar_global_cliente(
    empresa_id: int = Query(..., gt=0, description="ID da empresa"),
    termo: str = Query(..., min_length=1, description="Termo de busca"),
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
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Busca global em produtos, receitas e combos (para clientes).
    """
    service = BuscaGlobalService(db)
    return service.buscar(
        empresa_id=empresa_id,
        termo=termo,
        apenas_disponiveis=apenas_disponiveis,
        apenas_ativos=apenas_ativos,
        limit=limit,
    )


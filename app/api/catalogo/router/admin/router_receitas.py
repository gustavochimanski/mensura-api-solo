from fastapi import APIRouter, Depends, Body, Path, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from enum import Enum

from app.api.catalogo.services.service_receitas import ReceitasService
from app.api.catalogo.services.service_complemento import ComplementoService
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIn,
    ReceitaOut,
    ReceitaUpdate,
    ReceitaIngredienteIn,
    ReceitaIngredienteUpdate,
    ReceitaIngredienteOut,
    ReceitaComIngredientesOut,
    AdicionalIn,
    AdicionalOut,
    ClonarIngredientesRequest,
    ClonarIngredientesResponse,
)
from app.api.catalogo.schemas.schema_complemento import (
    VincularComplementosReceitaRequest,
    VincularComplementosReceitaResponse,
)
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/catalogo/admin/receitas",
    tags=["Admin - Catalogo - Receitas"],
    dependencies=[Depends(get_current_user)]
)


class TipoItemReceita(str, Enum):
    """Tipos de itens que podem ser vinculados a uma receita"""
    SUB_RECEITA = "sub-receita"
    PRODUTO = "produto"
    COMBO = "combo"


# Receitas - CRUD completo
@router.post("/", response_model=ReceitaOut, status_code=status.HTTP_201_CREATED)
def create_receita(
    body: ReceitaIn,
    db: Session = Depends(get_db),
):
    """Cria uma nova receita"""
    logger.info(f"[Receitas] Criar - empresa={body.empresa_id} nome={body.nome}")
    return ReceitasService(db).create_receita(body)


@router.get("/", response_model=list[ReceitaOut])
def list_receitas(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    search: Optional[str] = Query(None, description="Termo de busca em nome/descrição da receita"),
    db: Session = Depends(get_db),
):
    """
    Lista todas as receitas, com filtros opcionais.

    - `empresa_id`: filtra por empresa.
    - `ativo`: filtra por status ativo.
    - `search`: termo de busca em nome/descrição (case-insensitive).
    """
    logger.info(f"[Receitas] Listar - empresa_id={empresa_id} ativo={ativo} search={search!r}")
    return ReceitasService(db).list_receitas(empresa_id=empresa_id, ativo=ativo, search=search)


@router.get("/com-ingredientes", response_model=list[ReceitaComIngredientesOut])
def list_receitas_com_ingredientes(
    empresa_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    search: Optional[str] = Query(None, description="Termo de busca em nome/descrição da receita"),
    db: Session = Depends(get_db),
):
    """
    Lista todas as receitas com seus ingredientes incluídos, com filtros opcionais.

    - `empresa_id`: filtra por empresa.
    - `ativo`: filtra por status ativo.
    - `search`: termo de busca em nome/descrição (case-insensitive).
    """
    logger.info(f"[Receitas] Listar com ingredientes - empresa_id={empresa_id} ativo={ativo} search={search!r}")
    return ReceitasService(db).list_receitas_com_ingredientes(empresa_id=empresa_id, ativo=ativo, search=search)


# Itens de receitas (sub-receitas, produtos e combos)
# IMPORTANTE: Rotas sem parâmetros de path devem vir ANTES das rotas com parâmetros
# para evitar conflitos de roteamento (ex: /itens vs /{receita_id})
@router.get("/itens", response_model=list[ReceitaIngredienteOut])
def list_itens(
    receita_id: int = Query(..., description="ID da receita"),
    tipo: Optional[TipoItemReceita] = Query(None, description="Filtrar por tipo de item: sub-receita, produto ou combo"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os itens de uma receita.

    Pode filtrar por tipo usando o parâmetro `tipo`:
    - sub-receita: Outras receitas usadas como item
    - produto: Produtos normais
    - combo: Combos
    """
    return ReceitasService(db).list_ingredientes(receita_id, tipo=tipo.value if tipo else None)


@router.post("/itens", response_model=ReceitaIngredienteOut, status_code=status.HTTP_201_CREATED)
def add_item(
    body: ReceitaIngredienteIn,
    db: Session = Depends(get_db),
):
    """
    Adiciona um item (sub-receita, produto ou combo) a uma receita.
    """
    return ReceitasService(db).add_ingrediente(body)


@router.put("/itens/{receita_ingrediente_id}", response_model=ReceitaIngredienteOut)
def update_item(
    receita_ingrediente_id: int = Path(..., description="ID do vínculo item-receita (pode ser sub-receita, produto ou combo)"),
    body: ReceitaIngredienteUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """Atualiza a quantidade de um item (sub-receita, produto ou combo) em uma receita"""
    return ReceitasService(db).update_ingrediente(receita_ingrediente_id, body.quantidade)


@router.delete("/itens/{receita_ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    receita_ingrediente_id: int = Path(..., description="ID do vínculo item-receita (pode ser sub-receita, produto ou combo)"),
    db: Session = Depends(get_db),
):
    """Remove um item (sub-receita, produto ou combo) de uma receita (desvincula, mas não deleta o item original)"""
    ReceitasService(db).remove_ingrediente(receita_ingrediente_id)
    return None


@router.get("/{receita_id}", response_model=ReceitaOut)
def get_receita(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Busca uma receita por ID"""
    receita = ReceitasService(db).get_receita(receita_id)
    if not receita:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
    return receita


@router.put("/{receita_id}", response_model=ReceitaOut)
def update_receita(
    receita_id: int = Path(..., description="ID da receita"),
    body: ReceitaUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """Atualiza uma receita"""
    return ReceitasService(db).update_receita(receita_id, body)


@router.delete("/{receita_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receita(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Remove uma receita"""
    ReceitasService(db).delete_receita(receita_id)
    return None


# Adicionais
# IMPORTANTE: Rotas sem parâmetros de path devem vir ANTES das rotas com parâmetros
# para evitar conflitos de roteamento (ex: /adicionais vs /{receita_id}/adicionais)
@router.post("/adicionais", response_model=AdicionalOut, status_code=status.HTTP_201_CREATED)
def add_adicional(
    body: AdicionalIn,
    db: Session = Depends(get_db),
):
    """Adiciona um adicional a uma receita"""
    return ReceitasService(db).add_adicional(body)


@router.put("/adicionais/{adicional_id}", response_model=AdicionalOut)
def update_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """
    Atualiza um adicional de uma receita.
    Sincroniza o preço com o cadastro atual do produto (sempre busca do ProdutoEmpModel).
    """
    return ReceitasService(db).update_adicional(adicional_id)


@router.delete("/adicionais/{adicional_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_adicional(
    adicional_id: int = Path(..., description="ID do adicional"),
    db: Session = Depends(get_db),
):
    """Remove um adicional de uma receita"""
    ReceitasService(db).remove_adicional(adicional_id)
    return None


@router.get("/{receita_id}/adicionais", response_model=list[AdicionalOut])
def list_adicionais(
    receita_id: int = Path(..., description="ID da receita"),
    db: Session = Depends(get_db),
):
    """Lista todos os adicionais de uma receita"""
    return ReceitasService(db).list_adicionais(receita_id)


# Complementos (vinculação a receitas)
@router.put("/{receita_id}/complementos", response_model=VincularComplementosReceitaResponse, status_code=status.HTTP_200_OK)
def vincular_complementos_receita(
    receita_id: int = Path(..., description="ID da receita"),
    req: VincularComplementosReceitaRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Vincula múltiplos complementos a uma receita."""
    logger.info(f"[Receitas] Vincular complementos - receita={receita_id} complementos={req.complemento_ids}")
    service = ComplementoService(db)
    return service.vincular_complementos_receita(receita_id, req)


# Clonagem de ingredientes
@router.post("/clonar-ingredientes", response_model=ClonarIngredientesResponse, status_code=status.HTTP_200_OK)
def clonar_ingredientes(
    req: ClonarIngredientesRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Clona todos os ingredientes de uma receita para outra.
    
    - `receita_origem_id`: ID da receita de origem (de onde serão copiados os ingredientes)
    - `receita_destino_id`: ID da receita de destino (para onde serão copiados os ingredientes)
    
    Nota: Ingredientes duplicados (que já existem na receita destino) são ignorados.
    """
    logger.info(f"[Receitas] Clonar ingredientes - origem={req.receita_origem_id} destino={req.receita_destino_id}")
    return ReceitasService(db).clonar_ingredientes(req.receita_origem_id, req.receita_destino_id)


from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_complemento import (
    ComplementoResponse,
    CriarComplementoRequest,
    AtualizarComplementoRequest,
    AdicionalResponse,
    VincularComplementosProdutoRequest,
    VincularComplementosProdutoResponse,
    VincularItensComplementoRequest,
    VincularItensComplementoResponse,
    AtualizarOrdemItensRequest,
)
from app.api.catalogo.services.service_complemento import ComplementoService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/catalogo/admin/complementos",
    tags=["Admin - Catalogo - Complementos"],
    dependencies=[Depends(get_current_user)]
)


# ------ Complementos ------
@router.get("/", response_model=List[ComplementoResponse])
def listar_complementos(
    empresa_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os complementos de uma empresa."""
    logger.info(f"[Complementos] Listar - empresa={empresa_id} apenas_ativos={apenas_ativos}")
    service = ComplementoService(db)
    return service.listar_complementos(empresa_id, apenas_ativos)


@router.post("/", response_model=ComplementoResponse, status_code=status.HTTP_201_CREATED)
def criar_complemento(
    req: CriarComplementoRequest,
    db: Session = Depends(get_db),
):
    """Cria um novo complemento."""
    logger.info(f"[Complementos] Criar - empresa={req.empresa_id} nome={req.nome}")
    service = ComplementoService(db)
    return service.criar_complemento(req)


@router.get("/{complemento_id}", response_model=ComplementoResponse)
def buscar_complemento(
    complemento_id: int,
    db: Session = Depends(get_db),
):
    """Busca um complemento por ID."""
    logger.info(f"[Complementos] Buscar - id={complemento_id}")
    service = ComplementoService(db)
    return service.buscar_por_id(complemento_id)


@router.put("/{complemento_id}", response_model=ComplementoResponse)
def atualizar_complemento(
    complemento_id: int,
    req: AtualizarComplementoRequest,
    db: Session = Depends(get_db),
):
    """Atualiza um complemento existente."""
    logger.info(f"[Complementos] Atualizar - id={complemento_id}")
    service = ComplementoService(db)
    return service.atualizar_complemento(complemento_id, req)


@router.delete("/{complemento_id}", status_code=status.HTTP_200_OK)
def deletar_complemento(
    complemento_id: int,
    db: Session = Depends(get_db),
):
    """Deleta um complemento."""
    logger.info(f"[Complementos] Deletar - id={complemento_id}")
    service = ComplementoService(db)
    service.deletar_complemento(complemento_id)
    return {"message": "Complemento deletado com sucesso"}


@router.post("/produto/{cod_barras}/vincular", response_model=VincularComplementosProdutoResponse, status_code=status.HTTP_200_OK)
def vincular_complementos_produto(
    cod_barras: str,
    req: VincularComplementosProdutoRequest,
    db: Session = Depends(get_db),
):
    """Vincula múltiplos complementos a um produto."""
    logger.info(f"[Complementos] Vincular - produto={cod_barras} complementos={req.complemento_ids}")
    service = ComplementoService(db)
    return service.vincular_complementos_produto(cod_barras, req)


@router.get("/produto/{cod_barras}", response_model=List[ComplementoResponse])
def listar_complementos_produto(
    cod_barras: str,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os complementos de um produto específico."""
    logger.info(f"[Complementos] Listar por produto - produto={cod_barras}")
    service = ComplementoService(db)
    return service.listar_complementos_produto(cod_barras, apenas_ativos)


# ------ Vincular Itens a Complementos (N:N) ------
@router.post("/{complemento_id}/itens/vincular", response_model=VincularItensComplementoResponse, status_code=status.HTTP_200_OK)
def vincular_itens_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    req: VincularItensComplementoRequest = Depends(),
    db: Session = Depends(get_db),
):
    """Vincula múltiplos itens a um complemento."""
    logger.info(f"[Complementos] Vincular itens - complemento={complemento_id} itens={req.item_ids}")
    service = ComplementoService(db)
    return service.vincular_itens_complemento(complemento_id, req)


@router.delete("/{complemento_id}/itens/{item_id}", status_code=status.HTTP_200_OK)
def desvincular_item_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    item_id: int = Path(..., description="ID do item"),
    db: Session = Depends(get_db),
):
    """Remove a vinculação de um item com um complemento."""
    logger.info(f"[Complementos] Desvincular item - complemento={complemento_id} item={item_id}")
    service = ComplementoService(db)
    service.desvincular_item_complemento(complemento_id, item_id)
    return {"message": "Item desvinculado com sucesso"}


@router.get("/{complemento_id}/itens", response_model=List[AdicionalResponse])
def listar_itens_complemento(
    complemento_id: int = Path(..., description="ID do complemento"),
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os itens vinculados a um complemento."""
    logger.info(f"[Complementos] Listar itens - complemento={complemento_id}")
    service = ComplementoService(db)
    return service.listar_itens_complemento(complemento_id, apenas_ativos)


@router.put("/{complemento_id}/itens/ordem", status_code=status.HTTP_200_OK)
def atualizar_ordem_itens(
    complemento_id: int = Path(..., description="ID do complemento"),
    req: AtualizarOrdemItensRequest = Depends(),
    db: Session = Depends(get_db),
):
    """Atualiza a ordem dos itens em um complemento."""
    logger.info(f"[Complementos] Atualizar ordem itens - complemento={complemento_id}")
    service = ComplementoService(db)
    service.atualizar_ordem_itens(complemento_id, req)
    return {"message": "Ordem dos itens atualizada com sucesso"}


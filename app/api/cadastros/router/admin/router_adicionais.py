from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_adicional import (
    AdicionalResponse,
    CriarAdicionalRequest,
    AtualizarAdicionalRequest,
    VincularAdicionaisProdutoRequest,
)
from app.api.catalogo.services.service_adicional import AdicionalService
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/cadastros/admin/adicionais",
    tags=["Admin - Cadastros - Adicionais"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=List[AdicionalResponse])
def listar_adicionais(
    empresa_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os adicionais de uma empresa."""
    logger.info(f"[Adicionais] Listar - empresa={empresa_id} apenas_ativos={apenas_ativos}")
    service = AdicionalService(db)
    return service.listar_adicionais(empresa_id, apenas_ativos)


@router.post("/", response_model=AdicionalResponse, status_code=status.HTTP_201_CREATED)
def criar_adicional(
    req: CriarAdicionalRequest,
    db: Session = Depends(get_db),
):
    """Cria um novo adicional."""
    logger.info(f"[Adicionais] Criar - empresa={req.empresa_id} nome={req.nome}")
    service = AdicionalService(db)
    return service.criar_adicional(req)


@router.get("/{adicional_id}", response_model=AdicionalResponse)
def buscar_adicional(
    adicional_id: int,
    db: Session = Depends(get_db),
):
    """Busca um adicional por ID."""
    logger.info(f"[Adicionais] Buscar - id={adicional_id}")
    service = AdicionalService(db)
    return service.buscar_por_id(adicional_id)


@router.put("/{adicional_id}", response_model=AdicionalResponse)
def atualizar_adicional(
    adicional_id: int,
    req: AtualizarAdicionalRequest,
    db: Session = Depends(get_db),
):
    """Atualiza um adicional existente."""
    logger.info(f"[Adicionais] Atualizar - id={adicional_id}")
    service = AdicionalService(db)
    return service.atualizar_adicional(adicional_id, req)


@router.delete("/{adicional_id}", status_code=status.HTTP_200_OK)
def deletar_adicional(
    adicional_id: int,
    db: Session = Depends(get_db),
):
    """Deleta um adicional."""
    logger.info(f"[Adicionais] Deletar - id={adicional_id}")
    service = AdicionalService(db)
    return service.deletar_adicional(adicional_id)


@router.post("/produto/{cod_barras}/vincular", status_code=status.HTTP_200_OK)
def vincular_adicionais_produto(
    cod_barras: str,
    req: VincularAdicionaisProdutoRequest,
    db: Session = Depends(get_db),
):
    """Vincula múltiplos adicionais a um produto."""
    logger.info(f"[Adicionais] Vincular - produto={cod_barras} adicionais={req.adicional_ids}")
    service = AdicionalService(db)
    return service.vincular_adicionais_produto(cod_barras, req)


@router.get("/produto/{cod_barras}", response_model=List[AdicionalResponse])
def listar_adicionais_produto(
    cod_barras: str,
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
):
    """Lista todos os adicionais de um produto específico."""
    logger.info(f"[Adicionais] Listar por produto - produto={cod_barras}")
    service = AdicionalService(db)
    return service.listar_adicionais_produto(cod_barras, apenas_ativos)


from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.catalogo.schemas.schema_complemento import ComplementoResponse
from app.api.catalogo.services.service_complemento import ComplementoService
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository
from app.api.catalogo.repositories.repo_combo import ComboRepository
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/catalogo/client/complementos",
    tags=["Client - Catalogo - Complementos"],
)


@router.get("/produto/{cod_barras}", response_model=List[ComplementoResponse])
def listar_complementos_produto(
    cod_barras: str,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os complementos disponíveis para um produto específico, com seus adicionais.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Client] Listar por produto - produto={cod_barras} cliente={cliente.id}")
    service = ComplementoService(db)
    return service.listar_complementos_produto(cod_barras, apenas_ativos)


@router.get("/combo/{combo_id}", response_model=List[ComplementoResponse])
def listar_complementos_combo(
    combo_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os complementos disponíveis para um combo específico.

    Os complementos são obtidos diretamente da vinculação combo-complemento.
    Se não houver complementos vinculados diretamente, retorna lista vazia.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Client] Listar por combo - combo_id={combo_id} cliente={cliente.id}")
    
    # Busca o combo
    combo = db.query(ComboModel).filter(ComboModel.id == combo_id).first()
    
    if not combo or not combo.ativo:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Combo {combo_id} não encontrado ou inativo"
        )
    
    # Busca complementos vinculados diretamente ao combo
    service = ComplementoService(db)
    complementos = service.repo.listar_por_combo(combo_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
    
    return [service.complemento_to_response(c) for c in complementos]


@router.get("/receita/{receita_id}", response_model=List[ComplementoResponse])
def listar_complementos_receita(
    receita_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os complementos disponíveis para uma receita específica.

    Os complementos são obtidos diretamente da vinculação receita-complemento.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Client] Listar por receita - receita_id={receita_id} cliente={cliente.id}")
    
    # Busca a receita
    receita = db.query(ReceitaModel).filter(ReceitaModel.id == receita_id).first()
    
    if not receita or not receita.ativo or not receita.disponivel:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Receita {receita_id} não encontrada ou inativa"
        )
    
    # Busca complementos vinculados diretamente à receita
    service = ComplementoService(db)
    complementos = service.repo.listar_por_receita(receita_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
    
    return [service.complemento_to_response(c) for c in complementos]


from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_complemento import ComplementoResponse
from app.api.catalogo.services.service_complemento import ComplementoService
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/catalogo/public/complementos",
    tags=["Public - Catalogo - Complementos"],
)


@router.get("/produto/{cod_barras}", response_model=List[ComplementoResponse])
def listar_complementos_produto(
    cod_barras: str,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Lista todos os complementos disponíveis para um produto específico, com seus adicionais.
    
    Endpoint público - não requer autenticação.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Public] Listar por produto - produto={cod_barras}")
    service = ComplementoService(db)
    return service.listar_complementos_produto(cod_barras, apenas_ativos)


@router.get("/combo/{combo_id}", response_model=List[ComplementoResponse])
def listar_complementos_combo(
    combo_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Lista todos os complementos disponíveis para um combo específico.
    
    Os complementos são obtidos diretamente da vinculação combo-complemento.
    Se não houver complementos vinculados diretamente, retorna lista vazia.
    
    Endpoint público - não requer autenticação.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Public] Listar por combo - combo_id={combo_id}")
    
    # Busca o combo
    combo = db.query(ComboModel).filter(ComboModel.id == combo_id).first()
    
    if not combo or not combo.ativo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Combo {combo_id} não encontrado ou inativo"
        )
    
    # Busca complementos vinculados diretamente ao combo
    service = ComplementoService(db)
    complementos = service.repo.listar_por_combo(combo_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
    
    logger.info(f"[Complementos Public] Encontrados {len(complementos)} complementos para combo {combo_id}")
    
    if not complementos:
        logger.warning(f"[Complementos Public] Nenhum complemento encontrado para combo {combo_id} (apenas_ativos={apenas_ativos})")
    
    return [service.complemento_to_response(c) for c in complementos]


@router.get("/receita/{receita_id}", response_model=List[ComplementoResponse])
def listar_complementos_receita(
    receita_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Lista todos os complementos disponíveis para uma receita específica.
    
    Os complementos são obtidos diretamente da vinculação receita-complemento.
    
    Endpoint público - não requer autenticação.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Public] Listar por receita - receita_id={receita_id}")
    
    # Busca a receita
    receita = db.query(ReceitaModel).filter(ReceitaModel.id == receita_id).first()
    
    if not receita or not receita.ativo or not receita.disponivel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Receita {receita_id} não encontrada ou inativa"
        )
    
    # Busca complementos vinculados diretamente à receita
    service = ComplementoService(db)
    complementos = service.repo.listar_por_receita(receita_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
    
    logger.info(f"[Complementos Public] Encontrados {len(complementos)} complementos para receita {receita_id}")
    
    if not complementos:
        logger.warning(f"[Complementos Public] Nenhum complemento encontrado para receita {receita_id} (apenas_ativos={apenas_ativos})")
    
    return [service.complemento_to_response(c) for c in complementos]


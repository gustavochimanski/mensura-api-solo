from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.catalogo.schemas.schema_complemento import ComplementoResponse
from app.api.catalogo.services.service_complemento import ComplementoService
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository
from app.api.catalogo.repositories.repo_combo import ComboRepository
from app.api.catalogo.models.model_receita import ReceitaModel
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

    A lista é construída a partir dos produtos que compõem o combo,
    agregando os complementos vinculados a cada produto.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas complementos ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Complementos Client] Listar por combo - combo_id={combo_id} cliente={cliente.id}")
    
    # Busca o combo e seus produtos
    repo_combo = ComboRepository(db)
    combo = repo_combo.get_by_id(combo_id)
    
    if not combo or not combo.ativo:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Combo {combo_id} não encontrado ou inativo"
        )
    
    # Coleta todos os complementos dos produtos do combo
    repo_complemento = ComplementoRepository(db)
    complementos_unicos = {}
    
    for item in combo.itens:
        if item.produto_cod_barras:
            complementos = repo_complemento.listar_por_produto(
                item.produto_cod_barras,
                apenas_ativos=apenas_ativos,
                carregar_adicionais=True
            )
            for comp in complementos:
                if comp.id not in complementos_unicos:
                    complementos_unicos[comp.id] = comp
    
    service = ComplementoService(db)
    return [service.complemento_to_response(c) for c in complementos_unicos.values()]


@router.get("/receita/{receita_id}", response_model=List[ComplementoResponse])
def listar_complementos_receita(
    receita_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os complementos disponíveis para uma receita específica.

    Os complementos são obtidos a partir dos produtos vinculados à receita
    através dos ingredientes.

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
    
    # Receitas não têm produtos diretamente vinculados
    # Complementos de receitas devem ser gerenciados separadamente
    # Por enquanto, retorna lista vazia - pode ser expandido no futuro
    # se houver necessidade de vincular complementos diretamente a receitas
    return []


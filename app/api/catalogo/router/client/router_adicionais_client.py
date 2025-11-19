from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.catalogo.schemas.schema_adicional import AdicionalResponse
from app.api.catalogo.services.service_adicional import AdicionalService
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/catalogo/client/adicionais",
    tags=["Client - Catalogo - Adicionais"],
)


@router.get("/produto/{cod_barras}", response_model=List[AdicionalResponse])
def listar_adicionais_produto(
    cod_barras: str,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os adicionais disponíveis para um produto específico.

    Equivalente à rota antiga de cadastros, mas exposta no contexto de catálogo.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas adicionais ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Adicionais Catalogo Client] Listar por produto - produto={cod_barras} cliente={cliente.id}")
    service = AdicionalService(db)
    return service.listar_adicionais_produto(cod_barras, apenas_ativos)


@router.get("/combo/{combo_id}", response_model=List[AdicionalResponse])
def listar_adicionais_combo(
    combo_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os adicionais disponíveis para um combo específico.

    A lista é construída a partir dos produtos que compõem o combo,
    agregando os adicionais vinculados a cada produto.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas adicionais ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Adicionais Catalogo Client] Listar por combo - combo_id={combo_id} cliente={cliente.id}")
    service = AdicionalService(db)
    return service.listar_adicionais_combo(combo_id, apenas_ativos)


@router.get("/receita/{receita_id}", response_model=List[AdicionalResponse])
def listar_adicionais_receita(
    receita_id: int,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os adicionais disponíveis para uma receita específica.

    Os adicionais são obtidos a partir dos vínculos da receita (`ReceitaAdicionalModel`)
    com a tabela de adicionais do catálogo.

    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas adicionais ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Adicionais Catalogo Client] Listar por receita - receita_id={receita_id} cliente={cliente.id}")
    service = AdicionalService(db)
    return service.listar_adicionais_receita(receita_id, apenas_ativos)




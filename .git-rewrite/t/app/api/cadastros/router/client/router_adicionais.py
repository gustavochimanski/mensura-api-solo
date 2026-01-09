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
    prefix="/api/cadastros/client/adicionais",
    tags=["Client - Cadastros - Adicionais"]
)


@router.get("/produto/{cod_barras}", response_model=List[AdicionalResponse])
def listar_adicionais_produto(
    cod_barras: str,
    apenas_ativos: bool = Query(True),
    db: Session = Depends(get_db),
    cliente: ClienteModel = Depends(get_cliente_by_super_token),
):
    """
    Lista todos os adicionais disponíveis de um produto específico.
    
    Requer autenticação via header `X-Super-Token` do cliente.
    Retorna apenas adicionais ativos (a menos que apenas_ativos=false).
    """
    logger.info(f"[Adicionais Client] Listar por produto - produto={cod_barras} cliente={cliente.id}")
    service = AdicionalService(db)
    return service.listar_adicionais_produto(cod_barras, apenas_ativos)


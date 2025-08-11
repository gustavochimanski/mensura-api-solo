from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.delivery.schemas.cardapio_dv_schema import VitrineComProdutosResponse
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryOut
from app.api.delivery.services.cardapio_service import CardapioService
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery", tags=["Cardápio"])

@router.get("/cardapio", response_model=List[CategoriaDeliveryOut])
def listar_cardapio(
    empresa_id: int = Query(..., description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """
    Retorna a árvore (nível raiz) de categorias do cardápio para a empresa.
    """
    logger.info(f"[Cardápio] Listar categorias - empresa_id={empresa_id}")
    service = CardapioService(db)
    # Service padronizado conforme memória: listar_categorias
    return service.listar_categorias(empresa_id)

@router.get(
    "/produtos/vitrine-por-categoria",
    response_model=List[VitrineComProdutosResponse]
)
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Retorna as vitrines (e seus produtos) vinculadas a uma categoria.
    """
    logger.info(f"[Cardápio] Vitrines por categoria - empresa_id={empresa_id} categoria={cod_categoria}")
    service = CardapioService(db)
    # Service padronizado conforme memória: vitrines_com_produtos
    return service.vitrines_com_produtos(empresa_id, cod_categoria)

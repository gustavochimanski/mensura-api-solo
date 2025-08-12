from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.delivery.schemas.home_dv_schema import HomeResponse, VitrineComProdutosResponse
from app.api.delivery.services.home_service import HomeService
from app.database.db_connection import get_db
from app.utils.logger import logger
from typing import List

router = APIRouter(prefix="/api/delivery", tags=["Home"])

@router.get("/home", response_model=HomeResponse)
def listar_home(
    empresa_id: int = Query(..., description="ID da empresa"),
    only_home: bool = Query(False, description="Somente categorias raiz (parent_id nulo)"),
    db: Session = Depends(get_db),
):
    """
    Retorna categorias (raiz se only_home=True) e vitrines de home com produtos.
    """
    logger.info(f"[Home] empresa_id={empresa_id} only_home={only_home}")
    service = HomeService(db)
    return service.montar_home(empresa_id, only_home=only_home)

@router.get("/home/vitrine-por-categoria", response_model=List[VitrineComProdutosResponse])
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Retorna as vitrines (e seus produtos) vinculadas a uma categoria.
    """
    logger.info(f"[Home] Vitrines por categoria - empresa_id={empresa_id} categoria={cod_categoria}")
    service = HomeService(db)
    return service.vitrines_com_produtos(empresa_id, cod_categoria)

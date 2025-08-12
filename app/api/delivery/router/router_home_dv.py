# router_home_dv.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.delivery.schemas.home_dv_schema import HomeResponse, VitrineComProdutosResponse
from app.api.delivery.services.home_service import HomeService
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery", tags=["Home"])

@router.get("/home", response_model=HomeResponse)
def listar_home(
    empresa_id: int = Query(..., description="ID da empresa"),
    is_home: bool = Query(description="Filtra home: categorias raiz e/ou vitrines da home"),
    db: Session = Depends(get_db),
):
    logger.info(f"[Home] empresa_id={empresa_id} is_home={is_home}")
    return HomeService(db).montar_home(empresa_id, is_home=is_home)

@router.get("/home/vitrine-por-categoria", response_model=List[VitrineComProdutosResponse])
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: int = Query(...),
    is_home: bool = Query( description="Filtra vitrines por home"),
    db: Session = Depends(get_db),
):
    logger.info(f"[Home] Vitrines por categoria - empresa_id={empresa_id} categoria={cod_categoria} is_home={is_home}")
    return HomeService(db).vitrines_com_produtos(empresa_id, cod_categoria, is_home=is_home)

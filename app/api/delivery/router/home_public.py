# router_home_dv.py
from fastapi import APIRouter, Depends, Query, HTTPException, status  # <-- add HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.delivery.schemas.schema_home import HomeResponse, VitrineComProdutosResponse, CategoryPageResponse  # <-- add CategoryPageResponse
from app.api.delivery.services.service_home import HomeService
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/public/home", tags=["Public - Delivery - Home"])

@router.get("/home", response_model=HomeResponse)
def listar_home(
    empresa_id: int = Query(..., description="ID da empresa"),
    is_home: bool = Query(description="Filtra home: categorias raiz e/ou vitrines da home"),
    db: Session = Depends(get_db),
):
    logger.info(f"[Home] empresa_id={empresa_id} is_home={is_home}")
    return HomeService(db).montar_home(empresa_id, is_home=is_home)

# 🔁 ATUALIZADO: aceita cod_categoria OU slug
@router.get("/home/vitrine-por-categoria", response_model=List[VitrineComProdutosResponse])
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: Optional[int] = Query(None),
    slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if cod_categoria is None and not slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Informe cod_categoria ou slug")

    svc = HomeService(db)
    if cod_categoria is None and slug:
        cod_categoria = svc.resolve_categoria_id_por_slug(slug)

    logger.info(f"[Home] Vitrines por categoria - empresa_id={empresa_id} categoria={cod_categoria}")
    return svc.vitrines_com_produtos(empresa_id, cod_categoria)

# 🆕 NOVO: endpoint de página de categoria (dados focados)
@router.get("/home/categoria", response_model=CategoryPageResponse)
def get_categoria_page(
    empresa_id: int = Query(...),
    slug: str = Query(..., description="Slug da categoria atual"),
    db: Session = Depends(get_db),
):
    logger.info(f"[Home] Categoria page - empresa_id={empresa_id} slug={slug}")
    return HomeService(db).categoria_page(empresa_id, slug)

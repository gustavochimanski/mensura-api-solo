# router_home_dv.py
from fastapi import APIRouter, Depends, Query, HTTPException, status  # <-- add HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.cardapio.schemas.schema_home import HomeResponse, VitrineComProdutosResponse, CategoryPageResponse, LandingPageStoreResponse  # <-- add CategoryPageResponse
from app.database.db_connection import get_db
from app.utils.logger import logger
from app.api.cardapio.services.service_home import HomeService
from app.api.cardapio.services.dependencies import get_vitrine_contract

router = APIRouter(prefix="/api/cardapio/public/home", tags=["Public - Delivery - Home"])

@router.get("", response_model=HomeResponse)
def listar_home(
    empresa_id: int = Query(..., description="ID da empresa"),
    is_home: bool = Query(description="Filtra home: categorias raiz e/ou vitrines da home"),
    db: Session = Depends(get_db),
    vitrine_contract = Depends(get_vitrine_contract),
):
    logger.info(f"[Home] empresa_id={empresa_id} is_home={is_home}")
    return HomeService(db, vitrine_contract=vitrine_contract).montar_home(empresa_id, is_home=is_home)

# 🔁 ATUALIZADO: aceita cod_categoria OU slug
@router.get("/vitrine-por-categoria", response_model=List[VitrineComProdutosResponse])
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: Optional[int] = Query(None),
    slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    vitrine_contract = Depends(get_vitrine_contract),
):
    if cod_categoria is None and not slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Informe cod_categoria ou slug")

    svc = HomeService(db, vitrine_contract=vitrine_contract)
    if cod_categoria is None and slug:
        try:
            cod_categoria = svc.resolve_categoria_id_por_slug(empresa_id, slug)
        except ValueError as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

    logger.info(f"[Home] Vitrines por categoria - empresa_id={empresa_id} categoria={cod_categoria}")
    return svc.vitrines_com_produtos(empresa_id, cod_categoria)

# 🆕 NOVO: endpoint de página de categoria (dados focados)
@router.get("/categoria", response_model=CategoryPageResponse)
def get_categoria_page(
    empresa_id: int = Query(...),
    slug: str = Query(..., description="Slug da categoria atual"),
    db: Session = Depends(get_db),
    vitrine_contract = Depends(get_vitrine_contract),
):
    logger.info(f"[Home] Categoria page - empresa_id={empresa_id} slug={slug}")
    try:
        return HomeService(db, vitrine_contract=vitrine_contract).categoria_page(empresa_id, slug)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


# 🆕 Landing page store (sem categorias)
@router.get("/landingpage-store", response_model=LandingPageStoreResponse)
def get_landingpage_store(
    empresa_id: int = Query(...),
    is_home: bool = Query(False, description="Se true, filtra apenas vitrines marcadas como home"),
    db: Session = Depends(get_db),
    vitrine_contract = Depends(get_vitrine_contract),
):
    logger.info(f"[Home] Landingpage store - empresa_id={empresa_id} is_home={is_home}")
    return HomeService(db, vitrine_contract=vitrine_contract).landingpage_store(empresa_id, is_home=is_home)

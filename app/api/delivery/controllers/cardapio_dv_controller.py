from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.delivery.schemas.cardapio__dv_schema import  \
    VitrineComProdutosResponse
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryOut
from app.api.delivery.services.cardapio_dv_service import CardapioService
from app.database.db_connection import get_db

router = APIRouter(tags=["Cardapio"])

@router.get("/cardapio", response_model=List[CategoriaDeliveryOut])
def listar_cardapio(
    empresa_id: int,
    db: Session = Depends(get_db),
):

    service = CardapioService(db)
    return service.listar_cardapio(empresa_id)


@router.get("/produtos/vitrine-por-categoria", response_model=List[VitrineComProdutosResponse])
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: int = Query(...),
    db: Session = Depends(get_db)
):
    service = CardapioService(db)
    return service.buscar_vitrines_com_produtos(empresa_id, cod_categoria)

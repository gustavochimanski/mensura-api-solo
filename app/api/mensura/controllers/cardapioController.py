from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Union

from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import  \
    VitrineComProdutosResponse
from app.api.mensura.schemas.delivery.categorias.categoria_schema import CategoriaDeliveryOut
from app.api.mensura.services.CardapioService import CardapioService
from app.database.db_connection import get_db

router = APIRouter(tags=["Cardapio"])

@router.get("/cardapio", response_model=Union[List[CategoriaDeliveryOut], List[VitrineComProdutosResponse]])
def listar_cardapio(
    empresa_id: int,
    db: Session = Depends(get_db),
    is_home: bool = Query(...)
):
    service = CardapioService(db, is_home)

    if is_home:
        return service.buscar_vitrines_home(empresa_id)

    return service.listar_cardapio(empresa_id)


@router.get("/produtos/vitrine-por-categoria", response_model=List[VitrineComProdutosResponse])
def listar_vitrines_e_produtos_por_categoria(
    empresa_id: int = Query(...),
    cod_categoria: int = Query(...),
    db: Session = Depends(get_db)
):
    service = CardapioService(db)
    return service.buscar_vitrines_com_produtos(empresa_id, cod_categoria)

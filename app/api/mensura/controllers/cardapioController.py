from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.mensura.repositories.cardapio.CardapioRepository import CardapioRepository
from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import  \
    VitrineComProdutosResponse
from app.api.mensura.schemas.delivery.categorias.categoria_schema import CategoriaDeliveryOut
from app.api.mensura.services.CardapioService import CardapioService
from app.database.db_connection import get_db

router = APIRouter(tags=["Cardapio"])

@router.get("/cardapio", response_model=List[CategoriaDeliveryOut])
def listar_cardapio(empresa_id: int, db: Session = Depends(get_db)):
    repo = CardapioRepository(db)
    service = CardapioService(repo)
    return service.listar_cardapio(empresa_id)


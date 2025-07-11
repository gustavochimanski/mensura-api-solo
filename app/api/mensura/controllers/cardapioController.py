from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.mensura.repositories.cardapio.CardapioRepository import CardapioRepository
from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import CardapioCategProdutosResponse
from app.api.mensura.services.CardapioService import CardapioService
from app.database.db_connection import get_db

router = APIRouter(tags=["Cardapio"])

@router.get("/cardapio", response_model=List[CardapioCategProdutosResponse])
def listar_cardapio(cod_empresa: int = 1, db: Session = Depends(get_db)):
    repo = CardapioRepository(db)
    service = CardapioService(repo)
    return service.listar_cardapio(cod_empresa)
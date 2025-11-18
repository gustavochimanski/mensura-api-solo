from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.catalogo.contracts.receitas_contract import IReceitasContract
from app.api.catalogo.adapters.receitas_adapter import ReceitasAdapter


def get_receitas_contract(db: Session = Depends(get_db)) -> IReceitasContract:
    return ReceitasAdapter(db)



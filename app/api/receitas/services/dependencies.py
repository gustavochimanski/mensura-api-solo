from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.receitas.contracts.receitas_contract import IReceitasContract
from app.api.receitas.adapters.receitas_adapter import ReceitasAdapter


def get_receitas_contract(db: Session = Depends(get_db)) -> IReceitasContract:
    return ReceitasAdapter(db)




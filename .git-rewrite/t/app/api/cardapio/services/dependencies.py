from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.cardapio.contracts.vitrine_contract import IVitrineContract
from app.api.cardapio.adapters.vitrine_adapter import VitrineAdapter


def get_vitrine_contract(db: Session = Depends(get_db)) -> IVitrineContract:
    """Dependency para injetar o contract de vitrines."""
    return VitrineAdapter(db)


from __future__ import annotations
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.delivery.models.cupom_dv_model import CupomDescontoModel

class CupomRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[CupomDescontoModel]:
        return self.db.execute(select(CupomDescontoModel)).scalars().all()

    def get(self, id_: int) -> Optional[CupomDescontoModel]:
        return self.db.get(CupomDescontoModel, id_)

    def get_by_code(self, codigo: str) -> Optional[CupomDescontoModel]:
        return self.db.query(CupomDescontoModel).filter(CupomDescontoModel.codigo == codigo).first()

    def create(self, **data) -> CupomDescontoModel:
        obj = CupomDescontoModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: CupomDescontoModel, **data) -> CupomDescontoModel:
        for f, v in data.items():
            setattr(obj, f, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: CupomDescontoModel):
        self.db.delete(obj)
        self.db.commit()

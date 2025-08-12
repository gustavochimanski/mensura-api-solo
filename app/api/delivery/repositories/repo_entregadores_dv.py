from __future__ import annotations
from typing import Optional, List
from sqlalchemy.orm import Session

from app.api.delivery.models.entregador_dv_model import EntregadorDeliveryModel

class EntregadorRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[EntregadorDeliveryModel]:
        return self.db.query(EntregadorDeliveryModel).order_by(EntregadorDeliveryModel.created_at.desc()).all()

    def get(self, id_: int) -> Optional[EntregadorDeliveryModel]:
        return self.db.get(EntregadorDeliveryModel, id_)

    def create(self, **data) -> EntregadorDeliveryModel:
        obj = EntregadorDeliveryModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: EntregadorDeliveryModel, **data) -> EntregadorDeliveryModel:
        for f, v in data.items():
            setattr(obj, f, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: EntregadorDeliveryModel):
        self.db.delete(obj)
        self.db.commit()

# app/api/mensura/repositories/cliente_repository.py
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel


class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[ClienteDeliveryModel]:
        return (
            self.db
            .query(ClienteDeliveryModel)
            .filter(ClienteDeliveryModel.id == id)
            .first()
        )

    def list(self, skip: int = 0, limit: int = 100) -> List[ClienteDeliveryModel]:
        return (
            self.db
            .query(ClienteDeliveryModel)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, cliente: ClienteDeliveryModel) -> ClienteDeliveryModel:
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def update(self, cliente: ClienteDeliveryModel, data: dict) -> ClienteDeliveryModel:
        for key, value in data.items():
            setattr(cliente, key, value)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def delete(self, cliente: ClienteDeliveryModel) -> None:
        self.db.delete(cliente)
        self.db.commit()

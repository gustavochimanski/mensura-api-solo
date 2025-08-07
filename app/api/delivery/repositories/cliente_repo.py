# src/app/api/delivery/repositories/cliente_repository.py
from sqlalchemy.orm import Session

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.schemas.cliente_schema import ClienteCreate, ClienteUpdate
from app.database.db_connection import Base

class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_current(self) -> ClienteDeliveryModel | None:
        # Exemplo: supomos que há somente um cliente logado
        return self.db.query(ClienteDeliveryModel).first()

    def get_by_id(self, cliente_id: int) -> ClienteDeliveryModel | None:
        return self.db.get(ClienteDeliveryModel, cliente_id)

    def create(self, obj_in: ClienteCreate) -> ClienteDeliveryModel:
        db_obj = ClienteDeliveryModel(**obj_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db_obj: ClienteDeliveryModel,
        obj_in: ClienteUpdate
    ) -> ClienteDeliveryModel:
        obj_data = obj_in.model_dump(exclude_none=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

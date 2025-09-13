from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel

class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter_by(super_token=token).first()

    def get_by_telefone(self, telefone: str) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter_by(telefone=telefone).first()

    def get_by_email(self, email: str) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter_by(email=email).first()

    def get_by_cpf(self, cpf: str) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter_by(cpf=cpf).first()

    def get_by_id(self, id: int) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter(ClienteDeliveryModel.id == id).first()

    def list(self, ativo: Optional[bool] = None) -> List[ClienteDeliveryModel]:
        stmt = select(ClienteDeliveryModel)
        if ativo is not None:
            stmt = stmt.where(ClienteDeliveryModel.ativo.is_(ativo))
        return self.db.execute(stmt).scalars().all()

    def create(self, **data) -> ClienteDeliveryModel:
        obj = ClienteDeliveryModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, db_obj: ClienteDeliveryModel, **data) -> ClienteDeliveryModel:
        for k, v in data.items():
            setattr(db_obj, k, v)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def set_ativo(self, token: str, ativo: bool) -> Optional[ClienteDeliveryModel]:
        obj = self.get_by_token(token)
        if not obj:
            return None
        obj.ativo = ativo
        self.db.commit()
        self.db.refresh(obj)
        return obj

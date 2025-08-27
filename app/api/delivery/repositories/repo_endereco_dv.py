from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.schemas.schema_endereco_dv import EnderecoCreate, EnderecoUpdate
from app.api.delivery.models.endereco_dv_model import EnderecoDeliveryModel

class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_cliente(self, super_token: str):
        return (
            self.db.query(EnderecoDeliveryModel)
            .join(EnderecoDeliveryModel.cliente)
            .filter(EnderecoDeliveryModel.cliente.has(super_token=super_token))
            .order_by(EnderecoDeliveryModel.created_at.desc())
            .all()
        )

    def get_by_cliente(self, super_token: str, end_id: int):
        obj = (
            self.db.query(EnderecoDeliveryModel)
            .join(EnderecoDeliveryModel.cliente)
            .filter(
                EnderecoDeliveryModel.id == end_id,
                EnderecoDeliveryModel.cliente.has(super_token=super_token)
            )
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return obj

    def create(self, super_token: str, payload: EnderecoCreate):
        cliente = self.db.query(ClienteDeliveryModel).filter_by(super_token=super_token).first()
        obj = EnderecoDeliveryModel(**payload.model_dump(), cliente_id=cliente.id)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, super_token: str, end_id: int, payload: EnderecoUpdate):
        obj = self.get_by_cliente(super_token, end_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, super_token: str, end_id: int):
        obj = self.get_by_cliente(super_token, end_id)
        self.db.delete(obj)
        self.db.commit()

    def set_padrao(self, super_token: str, end_id: int):
        cliente = self.db.query(ClienteDeliveryModel).filter_by(super_token=super_token).first()
        self.db.query(EnderecoDeliveryModel).filter(
            EnderecoDeliveryModel.cliente_id == cliente.id
        ).update({"is_principal": False})
        obj = self.get_by_cliente(super_token, end_id)
        obj.is_principal = True
        self.db.commit()
        self.db.refresh(obj)
        return obj

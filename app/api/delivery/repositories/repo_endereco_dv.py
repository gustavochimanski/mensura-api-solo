from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.api.delivery.schemas.schema_endereco_dv import (EnderecoCreate, EnderecoUpdate)
from app.api.delivery.models.endereco_dv_model import EnderecoDeliveryModel

# --- Repository ---
class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_cliente(self, telefone_cliente: int) -> List[EnderecoDeliveryModel]:
        return (
            self.db.query(EnderecoDeliveryModel)
            .options(joinedload(EnderecoDeliveryModel.cliente))
            .filter(EnderecoDeliveryModel.cliente_telefone == telefone_cliente)
            .order_by(EnderecoDeliveryModel.created_at.desc())
            .all()
        )

    def get(self, end_id: int) -> EnderecoDeliveryModel:
        obj = (
            self.db.query(EnderecoDeliveryModel)
            .filter(EnderecoDeliveryModel.id == end_id)
            .first()
        )
        if not obj:
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return obj

    def create(self, payload: EnderecoCreate) -> EnderecoDeliveryModel:
        obj = EnderecoDeliveryModel(**payload.model_dump())
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, end_id: int, payload: EnderecoUpdate) -> EnderecoDeliveryModel:
        obj = self.get(end_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, end_id: int) -> None:
        obj = self.get(end_id)
        self.db.delete(obj)
        self.db.commit()

    def set_padrao(self, cliente_id: int, end_id: int) -> EnderecoDeliveryModel:
        # Zera padrão dos demais
        self.db.query(EnderecoDeliveryModel).filter(
            EnderecoDeliveryModel.cliente_id == cliente_id
        ).update({"is_principal": False})
        # Define padrão no escolhido
        obj = self.get(end_id)
        obj.is_principal = True
        self.db.commit()
        self.db.refresh(obj)
        return obj


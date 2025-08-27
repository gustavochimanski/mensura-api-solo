from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List
from app.api.delivery.schemas.schema_endereco_dv import EnderecoCreate, EnderecoUpdate
from app.api.delivery.models.endereco_dv_model import EnderecoDeliveryModel

class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_cliente(self, cliente_telefone: str) -> List[EnderecoDeliveryModel]:
        return (
            self.db.query(EnderecoDeliveryModel)
            .options(joinedload(EnderecoDeliveryModel.cliente))
            .filter(EnderecoDeliveryModel.cliente_telefone == cliente_telefone)
            .order_by(EnderecoDeliveryModel.created_at.desc())
            .all()
        )

    def get_by_cliente(self, cliente_telefone: str, end_id: int) -> EnderecoDeliveryModel:
        obj = self.db.query(EnderecoDeliveryModel).filter(
            EnderecoDeliveryModel.id == end_id,
            EnderecoDeliveryModel.cliente_telefone == cliente_telefone
        ).first()
        if not obj:
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return obj

    def create(self, cliente_telefone: str, payload: EnderecoCreate) -> EnderecoDeliveryModel:
        obj = EnderecoDeliveryModel(**payload.model_dump(), cliente_telefone=cliente_telefone)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, cliente_telefone: str, end_id: int, payload: EnderecoUpdate) -> EnderecoDeliveryModel:
        obj = self.get_by_cliente(cliente_telefone, end_id)
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, cliente_telefone: str, end_id: int):
        obj = self.get_by_cliente(cliente_telefone, end_id)
        self.db.delete(obj)
        self.db.commit()

    def set_padrao(self, cliente_telefone: str, end_id: int) -> EnderecoDeliveryModel:
        # Zera padrão dos demais
        self.db.query(EnderecoDeliveryModel).filter(
            EnderecoDeliveryModel.cliente_telefone == cliente_telefone
        ).update({"is_principal": False})
        # Define padrão no escolhido
        obj = self.get_by_cliente(cliente_telefone, end_id)
        obj.is_principal = True
        self.db.commit()
        self.db.refresh(obj)
        return obj

from __future__ import annotations
from typing import Optional, List

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.api.delivery.models.model_entregador_dv import EntregadorDeliveryModel
from app.api.mensura.models.association_tables import entregador_empresa


class EntregadorRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[EntregadorDeliveryModel]:
        return self.db.query(EntregadorDeliveryModel).order_by(EntregadorDeliveryModel.created_at.desc()).all()

    def get(self, id_: int) -> Optional[EntregadorDeliveryModel]:
        return self.db.get(EntregadorDeliveryModel, id_)

    def create_with_empresa(self, **data) -> EntregadorDeliveryModel:
        empresa_id = data.pop("empresa_id", None)  # remove para não quebrar a tabela
        obj = EntregadorDeliveryModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)

        if empresa_id:
            stmt = insert(entregador_empresa).values(
                entregador_id=obj.id,
                empresa_id=empresa_id
            ).prefix_with("ON CONFLICT DO NOTHING")
            self.db.execute(stmt)
            self.db.commit()

        return obj


    def update(self, obj: EntregadorDeliveryModel, **data) -> EntregadorDeliveryModel:
        for f, v in data.items():
            setattr(obj, f, v)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def vincular_empresa(self, entregador_id: int, empresa_id: int):
        stmt = insert(entregador_empresa).values(
            entregador_id=entregador_id,
            empresa_id=empresa_id
        ).prefix_with("ON CONFLICT DO NOTHING")  # evita duplicidade
        self.db.execute(stmt)
        self.db.commit()

    def delete(self, obj: EntregadorDeliveryModel):
        self.db.delete(obj)
        self.db.commit()

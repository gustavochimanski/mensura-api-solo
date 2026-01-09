from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
from app.api.cadastros.models.association_tables import entregador_empresa


class EntregadorRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> List[EntregadorDeliveryModel]:
        return self.db.query(EntregadorDeliveryModel).order_by(EntregadorDeliveryModel.created_at.desc()).all()

    def get(self, id_: int) -> Optional[EntregadorDeliveryModel]:
        return self.db.get(EntregadorDeliveryModel, id_)

    def create_with_empresa(self, **data) -> EntregadorDeliveryModel:
        empresa_id = data.pop("empresa_id", None)
        obj = EntregadorDeliveryModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)

        if empresa_id:
            stmt = insert(entregador_empresa).values(
                entregador_id=obj.id,
                empresa_id=empresa_id
            ).on_conflict_do_nothing()
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
        ).on_conflict_do_nothing()
        self.db.execute(stmt)
        self.db.commit()

    def desvincular_empresa(self, entregador_id: int, empresa_id: int):
        """
        Remove o vínculo do entregador com a empresa.
        """
        self.db.execute(
            entregador_empresa.delete().where(
                (entregador_empresa.c.entregador_id == entregador_id) &
                (entregador_empresa.c.empresa_id == empresa_id)
            )
        )
        self.db.commit()

    def delete(self, obj: EntregadorDeliveryModel):
        self.db.delete(obj)
        self.db.commit()


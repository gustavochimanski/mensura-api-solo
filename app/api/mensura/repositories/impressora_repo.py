# app/api/mensura/repositories/impressora_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.api.mensura.models.impressora_model import ImpressoraModel
from app.api.mensura.schemas.schema_impressora import ImpressoraCreate, ImpressoraUpdate

class ImpressoraRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_impressora(self, impressora_data: ImpressoraCreate) -> ImpressoraModel:
        db_impressora = ImpressoraModel(
            nome=impressora_data.nome,
            nome_impressora=impressora_data.nome_impressora,
            config=impressora_data.config.model_dump(),
            empresa_id=impressora_data.empresa_id
        )
        self.db.add(db_impressora)
        self.db.commit()
        self.db.refresh(db_impressora)
        return db_impressora

    def get_impressora_by_id(self, impressora_id: int) -> Optional[ImpressoraModel]:
        return self.db.query(ImpressoraModel).filter(ImpressoraModel.id == impressora_id).first()

    def get_impressoras_by_empresa(self, empresa_id: int) -> List[ImpressoraModel]:
        return self.db.query(ImpressoraModel).filter(ImpressoraModel.empresa_id == empresa_id).all()

    def update_impressora(self, impressora_id: int, impressora_data: ImpressoraUpdate) -> Optional[ImpressoraModel]:
        db_impressora = self.get_impressora_by_id(impressora_id)
        if not db_impressora:
            return None

        update_data = impressora_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "config" and value is not None:
                setattr(db_impressora, field, value.model_dump())
            else:
                setattr(db_impressora, field, value)

        self.db.commit()
        self.db.refresh(db_impressora)
        return db_impressora

    def delete_impressora(self, impressora_id: int) -> bool:
        db_impressora = self.get_impressora_by_id(impressora_id)
        if not db_impressora:
            return False

        self.db.delete(db_impressora)
        self.db.commit()
        return True

    def list_impressoras(self, skip: int = 0, limit: int = 100) -> List[ImpressoraModel]:
        return self.db.query(ImpressoraModel).offset(skip).limit(limit).all()

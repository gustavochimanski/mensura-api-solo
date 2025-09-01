from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.repositories.repo_cupom import CupomRepository
from app.api.delivery.schemas.schema_cupom import CupomCreate, CupomUpdate

class CuponsService:
    def __init__(self, db: Session):
        self.repo = CupomRepository(db)

    def list(self):
        return self.repo.list()

    def get(self, id_: int):
        obj = self.repo.get(id_)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        return obj

    def create(self, data: CupomCreate):
        return self.repo.create(**data.model_dump(exclude_unset=True))

    def update(self, id_: int, data: CupomUpdate):
        obj = self.get(id_)
        return self.repo.update(obj, **data.model_dump(exclude_none=True))

    def delete(self, id_: int):
        obj = self.get(id_)
        self.repo.delete(obj)
        return {"ok": True}

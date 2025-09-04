from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.repositories.repo_cupom import CupomRepository
from app.api.delivery.models.model_parceiros_dv import ParceiroModel
from app.api.delivery.schemas.schema_cupom import CupomCreate, CupomUpdate

class CuponsService:
    def __init__(self, db: Session):
        self.repo = CupomRepository(db)
        self.db = db

    def list(self):
        return self.repo.list()

    def get(self, id_: int):
        obj = self.repo.get(id_)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        return obj

    def create(self, data: CupomCreate):
        payload = data.model_dump(exclude_unset=True)
        if payload.get("monetizado") and payload.get("parceiro_id"):
            parceiro = self.db.get(ParceiroModel, payload["parceiro_id"])
            if not parceiro or not parceiro.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")
        return self.repo.create(**payload)

    def update(self, id_: int, data: CupomUpdate):
        obj = self.get(id_)
        payload = data.model_dump(exclude_none=True)
        if payload.get("monetizado") and payload.get("parceiro_id"):
            parceiro = self.db.get(ParceiroModel, payload["parceiro_id"])
            if not parceiro or not parceiro.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")
        return self.repo.update(obj, **payload)

    def delete(self, id_: int):
        obj = self.get(id_)
        self.repo.delete(obj)
        return {"ok": True}

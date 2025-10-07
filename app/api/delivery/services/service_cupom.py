from typing import List
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.api.delivery.models.model_cupom_dv import CupomDescontoModel
from app.api.delivery.models.model_parceiros_dv import ParceiroModel
from app.api.delivery.repositories.repo_cupom import CupomRepository
from app.api.delivery.schemas.schema_cupom import CupomCreate, CupomUpdate

class CuponsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CupomRepository(db)

    # ---------------- CUPOM ----------------
    def create(self, data: CupomCreate) -> CupomDescontoModel:
        cupom_data = data.model_dump()

        # Se monetizado=True, valida parceiro
        if cupom_data.get("monetizado"):
            parceiro = self.db.get(ParceiroModel, cupom_data.get("parceiro_id"))
            if not parceiro or not parceiro.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")
        else:
            cupom_data["parceiro_id"] = None  # ignora parceiro se não monetizado

        cupom = CupomDescontoModel(**cupom_data)
        self.repo.create(cupom)
        return cupom

    def update(self, cupom_id: int, data: CupomUpdate) -> CupomDescontoModel:
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")

        payload = data.model_dump(exclude_none=True)

        # Só atualiza parceiro se monetizado=True
        if payload.get("monetizado") or (payload.get("parceiro_id") and cupom.monetizado):
            parceiro_id = payload.get("parceiro_id")
            if parceiro_id:
                parceiro = self.db.get(ParceiroModel, parceiro_id)
                if not parceiro or not parceiro.ativo:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")
        else:
            payload["parceiro_id"] = None  # ignora parceiro se não monetizado

        for key, value in payload.items():
            setattr(cupom, key, value)

        self.repo.update(cupom)
        return cupom

    # ---------------- LIST COM LINKS ----------------
    def list(self) -> List[CupomDescontoModel]:
        return self.db.query(CupomDescontoModel).all()

    def list_by_parceiro(self, parceiro_id: int) -> List[CupomDescontoModel]:
        parceiro = self.db.get(ParceiroModel, parceiro_id)
        if not parceiro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parceiro não encontrado")

        return (
            self.db.query(CupomDescontoModel)
            .filter(CupomDescontoModel.parceiro_id == parceiro_id)
            .all()
        )

    def get(self, cupom_id: int) -> CupomDescontoModel:
        cupom = (
            self.db.query(CupomDescontoModel)
            .filter(CupomDescontoModel.id == cupom_id)
            .first()
        )
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        return cupom

    def delete(self, cupom_id: int):
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        self.repo.delete(cupom)


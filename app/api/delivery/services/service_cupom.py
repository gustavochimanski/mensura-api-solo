from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.api.delivery.models.model_cupom_dv import CupomDescontoModel
from app.api.delivery.models.model_parceiros_dv import ParceiroModel
from app.api.delivery.repositories.repo_cupom import CupomRepository
from app.api.delivery.schemas.schema_cupom import CupomCreate, CupomUpdate

class CuponsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CupomRepository(db)

    # ---------------- CREATE ----------------
    def create(self, data: CupomCreate) -> CupomDescontoModel:
        # Verifica se parceiro existe e está ativo
        parceiro = self.db.get(ParceiroModel, data.parceiro_id)
        if not parceiro or not parceiro.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")

        cupom = CupomDescontoModel(**data.model_dump())
        self.repo.create(cupom)
        return cupom

    # ---------------- UPDATE ----------------
    def update(self, cupom_id: int, data: CupomUpdate) -> CupomDescontoModel:
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")

        payload = data.model_dump(exclude_none=True)

        # Atualiza parceiro se informado
        if "parceiro_id" in payload:
            parceiro = self.db.get(ParceiroModel, payload["parceiro_id"])
            if not parceiro or not parceiro.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")

        for key, value in payload.items():
            setattr(cupom, key, value)

        self.repo.update(cupom)
        return cupom

    # ---------------- LIST ----------------
    def list(self) -> List[CupomDescontoModel]:
        return self.repo.list()

    # ---------------- GET ----------------
    def get(self, cupom_id: int) -> CupomDescontoModel:
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        return cupom

    # ---------------- DELETE ----------------
    def delete(self, cupom_id: int):
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        self.repo.delete(cupom)

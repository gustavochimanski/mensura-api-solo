from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.models.model_cupom_dv import CupomDescontoModel
from app.api.delivery.repositories.repo_cupom import CupomRepository
from app.api.delivery.models.model_parceiros_dv import ParceiroModel, CupomParceiroLinkModel
from app.api.delivery.schemas.schema_cupom import CupomCreate, CupomUpdate


class CuponsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CupomRepository(db)

    # ---------------- CREATE ----------------
    def create(self, data: CupomCreate):
        payload = data.model_dump(exclude_unset=True)
        parceiros_ids = payload.pop("parceiros_ids") or []

        cupom = CupomDescontoModel(**payload)
        self.repo.create(cupom)

        if payload.get("monetizado") and parceiros_ids:
            self._vincular_parceiros(cupom, parceiros_ids)
        return cupom

    # ---------------- UPDATE ----------------
    def update(self, id_: int, data: CupomUpdate):
        cupom = self.repo.get(id_)
        payload = data.model_dump(exclude_none=True)
        parceiros_ids = payload.pop("parceiros_ids", None)

        for k, v in payload.items():
            setattr(cupom, k, v)
        self.repo.update(cupom)

        if "monetizado" in payload:
            if payload["monetizado"] and parceiros_ids:
                self._vincular_parceiros(cupom, parceiros_ids)
            elif not payload["monetizado"]:
                cupom.parceiro_links.clear()
                self.db.commit()

        return cupom

    # ---------------- LIST ----------------
    def list(self) -> List[CupomDescontoModel]:
        return self.repo.list()

    # ---------------- GET ----------------
    def get(self, id_: int) -> CupomDescontoModel:
        cupom = self.repo.get(id_)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        return cupom

    # ---------------- DELETE ----------------
    def delete(self, id_: int):
        cupom = self.repo.get(id_)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        self.repo.delete(cupom)

    # ---------------- VINCULAR PARCEIROS ----------------
    def _vincular_parceiros(self, cupom: CupomDescontoModel, parceiros_ids: List[int]):
        parceiros = []
        for pid in parceiros_ids:
            parceiro = self.db.get(ParceiroModel, pid)
            if not parceiro or not parceiro.ativo:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Parceiro {pid} inválido ou inativo"
                )
            parceiros.append(parceiro)

        cupom.parceiro_links.clear()

        for parceiro in parceiros:
            link = CupomParceiroLinkModel(
                cupom=cupom,
                parceiro=parceiro,
                valor_por_indicacao=cupom.valor_por_lead or 0,
                link_whatsapp=(
                    f"https://api.whatsapp.com/send?text=Olá! Vim pelo {parceiro.nome}. "
                    f"Código do cupom: {cupom.codigo}"
                )
            )
            self.db.add(link)

        self.db.commit()
        self.db.refresh(cupom)

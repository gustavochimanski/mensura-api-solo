from sqlalchemy.orm import Session
from typing import Optional
from fastapi import HTTPException, status

from app.api.cadastros.repositories.repo_parceiros import ParceirosRepository

from app.api.cadastros.schemas.schema_parceiros import ParceiroIn, BannerParceiroIn
from app.api.cadastros.models.model_parceiros import BannerParceiroModel

class ParceirosService:
    def __init__(self, db: Session):
        self.repo = ParceirosRepository(db)

    # Parceiros
    def create_parceiro(self, data: ParceiroIn):
        return self.repo.create_parceiro(data)

    def list_parceiros(self):
        return self.repo.list_parceiros()

    def get_parceiro(self, parceiro_id: int):
        return self.repo.get_parceiro(parceiro_id)

    def get_parceiro_completo(self, parceiro_id: int):
        return self.repo.get_parceiro_completo(parceiro_id)

    def update_parceiro(self, parceiro_id: int, data: dict):
        return self.repo.update_parceiro(parceiro_id, data)

    def delete_parceiro(self, parceiro_id: int):
        return self.repo.delete_parceiro(parceiro_id)

    # Banners
    def _preparar_payload_banner(
        self,
        payload: dict,
        atual: Optional[BannerParceiroModel] = None,
    ) -> dict:
        # Normaliza link vazio -> None (quando vier via form/json)
        if "link_redirecionamento" in payload and not payload["link_redirecionamento"]:
            payload["link_redirecionamento"] = None

        return payload

    def create_banner(self, data: BannerParceiroIn):
        payload = self._preparar_payload_banner(data.model_dump())
        return self.repo.create_banner(BannerParceiroIn(**payload))

    def list_banners(self, parceiro_id: Optional[int] = None):
        return self.repo.list_banners(parceiro_id)

    def get_banner(self, banner_id: int):
        return self.repo.get_banner(banner_id)

    def update_banner(self, banner_id: int, data: dict):
        # Mesma regra do create aplicável no update
        atual = self.repo.get_banner(banner_id)
        payload = self._preparar_payload_banner(dict(data), atual)
        return self.repo.update_banner(banner_id, payload)

    def delete_banner(self, banner_id: int):
        return self.repo.delete_banner(banner_id)

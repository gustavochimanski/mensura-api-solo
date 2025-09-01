# app/api/delivery/services/parceiros_service.py
from sqlalchemy.orm import Session
from app.api.delivery.repositories.repo_parceiros import ParceirosRepository
from app.api.delivery.schemas.schema_parceiros import ParceiroIn, BannerParceiroIn

class ParceirosService:
    def __init__(self, db: Session):
        self.repo = ParceirosRepository(db)

    # Parceiros
    def create_parceiro(self, data: ParceiroIn):
        return self.repo.create_parceiro(data)

    def list_parceiros(self):
        return self.repo.list_parceiros()

    def update_parceiro(self, parceiro_id: int, data: dict):
        return self.repo.update_parceiro(parceiro_id, data)

    def delete_parceiro(self, parceiro_id: int):
        return self.repo.delete_parceiro(parceiro_id)

    # Banners
    def create_banner(self, data: BannerParceiroIn):
        return self.repo.create_banner(data)

    def list_banners(self, parceiro_id: int = None):
        return self.repo.list_banners(parceiro_id)

    def update_banner(self, banner_id: int, data: dict):
        return self.repo.update_banner(banner_id, data)

    def delete_banner(self, banner_id: int):
        return self.repo.delete_banner(banner_id)

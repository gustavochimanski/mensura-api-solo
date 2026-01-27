from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.api.cadastros.models.model_cupom import CupomDescontoModel
from app.api.cadastros.models.model_parceiros import ParceiroModel, BannerParceiroModel
from app.api.cadastros.schemas.schema_parceiros import ParceiroIn, BannerParceiroIn

class ParceirosRepository:
    def __init__(self, db: Session):
        self.db = db

    # Parceiros
    def create_parceiro(self, data: ParceiroIn) -> ParceiroModel:
        if self.db.query(ParceiroModel).filter_by(nome=data.nome).first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro já existe")
        p = ParceiroModel(nome=data.nome, ativo=data.ativo)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def list_parceiros(self) -> List[ParceiroModel]:
        return (
            self.db.query(ParceiroModel)
            .options(joinedload(ParceiroModel.banners).joinedload(BannerParceiroModel.categoria))
            .all()
        )

    def get_parceiro(self, parceiro_id: int) -> ParceiroModel:
        p = (
            self.db.query(ParceiroModel)
            .options(joinedload(ParceiroModel.banners).joinedload(BannerParceiroModel.categoria))
            .filter_by(id=parceiro_id)
            .first()
        )
        if not p:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parceiro não encontrado")
        return p

    def get_parceiro_completo(self, parceiro_id: int):
        parceiro = (
            self.db.query(ParceiroModel)
            .options(
                joinedload(ParceiroModel.cupons),
                joinedload(ParceiroModel.banners).joinedload(BannerParceiroModel.categoria)
            )
            .filter(ParceiroModel.id == parceiro_id)
            .first()
        )
        if not parceiro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parceiro não encontrado")
        return parceiro

    def update_parceiro(self, parceiro_id: int, data: dict) -> ParceiroModel:
        p = self.get_parceiro(parceiro_id)
        for key in ["nome", "ativo"]:
            if key in data:
                setattr(p, key, data[key])
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete_parceiro(self, parceiro_id: int) -> None:
        p = self.get_parceiro(parceiro_id)
        self.db.delete(p)
        self.db.commit()

    # Banners
    def create_banner(self, data: BannerParceiroIn) -> BannerParceiroModel:
        b = BannerParceiroModel(
            nome=data.nome,
            parceiro_id=data.parceiro_id,
            categoria_id=data.categoria_id,
            link_redirecionamento=data.link_redirecionamento,
            ativo=data.ativo,
            tipo_banner=data.tipo_banner,
            imagem=data.imagem
        )
        self.db.add(b)
        self.db.commit()
        self.db.refresh(b)
        return b

    def list_banners(self, parceiro_id: Optional[int] = None) -> List[BannerParceiroModel]:
        query = self.db.query(BannerParceiroModel)
        if parceiro_id:
            query = query.filter_by(parceiro_id=parceiro_id)
        return query.all()

    def get_banner(self, banner_id: int) -> BannerParceiroModel:
        b = self.db.query(BannerParceiroModel).filter_by(id=banner_id).first()
        if not b:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Banner não encontrado")
        return b

    def update_banner(self, banner_id: int, data: dict) -> BannerParceiroModel:
        b = self.get_banner(banner_id)
        for key in ["nome", "imagem", "tipo_banner", "parceiro_id", "ativo", "categoria_id", "link_redirecionamento"]:
            if key in data:
                setattr(b, key, data[key])
        self.db.commit()
        self.db.refresh(b)
        return b

    def delete_banner(self, banner_id: int) -> None:
        b = self.get_banner(banner_id)
        self.db.delete(b)
        self.db.commit()

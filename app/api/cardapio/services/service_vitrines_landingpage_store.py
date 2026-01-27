from __future__ import annotations

from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.cardapio.models.model_vitrine import VitrinesLandingpageStoreModel
from app.api.cardapio.repositories.repo_vitrines_landingpage_store import VitrineLandingpageStoreRepository
from app.api.cardapio.schemas.schema_vitrine import CriarVitrineRequest, AtualizarVitrineRequest
from app.api.catalogo.models.model_receita import ReceitaModel


class VitrinesLandingpageStoreService:
    """
    Service (landingpage_store): validações e tradução para HTTP.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = VitrineLandingpageStoreRepository(db)

    def search(
        self,
        *,
        empresa_id: int,
        q: Optional[str],
        is_home: Optional[bool],
        limit: int,
        offset: int,
    ) -> List[VitrinesLandingpageStoreModel]:
        return self.repo.search(
            empresa_id=empresa_id,
            q=q,
            is_home=is_home,
            limit=limit,
            offset=offset,
        )

    def create(self, req: CriarVitrineRequest) -> VitrinesLandingpageStoreModel:
        # cod_categoria não é aplicável na landingpage_store
        if req.cod_categoria is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="cod_categoria não é permitido quando landingpage_true=true",
            )
        try:
            return self.repo.create(
                empresa_id=req.empresa_id,
                titulo=req.titulo,
                is_home=bool(req.is_home),
            )
        except IntegrityError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conflito de dados ao criar vitrine")

    def update(
        self, vitrine_id: int, req: AtualizarVitrineRequest, *, empresa_id: int
    ) -> VitrinesLandingpageStoreModel:
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")

        if req.cod_categoria is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="cod_categoria não é permitido quando landingpage_true=true",
            )

        try:
            return self.repo.update(
                v,
                titulo=req.titulo,
                ordem=req.ordem,
                is_home=req.is_home,
            )
        except IntegrityError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conflito de dados ao atualizar vitrine")

    def delete(self, vitrine_id: int, *, empresa_id: int) -> None:
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        if self.repo.has_vinculos(vitrine_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir. Existem produtos vinculados.",
            )
        self.repo.delete(v)

    def set_is_home(self, vitrine_id: int, is_home: bool, *, empresa_id: int) -> VitrinesLandingpageStoreModel:
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        return self.repo.set_is_home(v, is_home)

    def vincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        if not self.repo.exists_prod_emp(empresa_id=empresa_id, cod_barras=cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto da empresa não encontrado")
        ok = self.repo.vincular_produto(vitrine_id=vitrine_id, cod_barras=cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular produto")
        return {"ok": True}

    def desvincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        if not self.repo.exists_prod_emp(empresa_id=empresa_id, cod_barras=cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto da empresa não encontrado")
        ok = self.repo.desvincular_produto(vitrine_id=vitrine_id, cod_barras=cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto não estava vinculado")
        return {"ok": True}

    def vincular_combo(self, vitrine_id: int, combo_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        ok = self.repo.vincular_combo(vitrine_id=vitrine_id, combo_id=combo_id)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular combo")
        return {"ok": True}

    def desvincular_combo(self, vitrine_id: int, combo_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        ok = self.repo.desvincular_combo(vitrine_id=vitrine_id, combo_id=combo_id)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Combo não estava vinculado")
        return {"ok": True}

    def vincular_receita(self, vitrine_id: int, receita_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        receita = self.db.query(ReceitaModel).filter(ReceitaModel.id == receita_id).first()
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receita não encontrada")
        ok = self.repo.vincular_receita(vitrine_id=vitrine_id, receita_id=receita_id)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular receita")
        return {"ok": True}

    def desvincular_receita(self, vitrine_id: int, receita_id: int, *, empresa_id: int):
        v = self.repo.get_vitrine_by_id(vitrine_id, empresa_id=empresa_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        ok = self.repo.desvincular_receita(vitrine_id=vitrine_id, receita_id=receita_id)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receita não estava vinculada")
        return {"ok": True}


from __future__ import annotations
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.delivery.models.vitrine_dv_model import VitrinesModel
from app.api.delivery.repositories.repo_vitrines import VitrineRepository
from app.api.delivery.schemas.schema_vitrine import (
    CriarVitrineRequest,
    AtualizarVitrineRequest,
)


class VitrinesService:
    """
    Orquestra validações e traduz exceções técnicas para HTTP.
    """
    def __init__(self, db: Session):
        self.repo = VitrineRepository(db)

    # -------- Search --------
    def search(
        self,
        *,
        q: Optional[str],
        cod_categoria: Optional[int],
        is_home: Optional[bool],
        limit: int,
        offset: int,
    ) -> List[VitrinesModel]:
        return self.repo.search(
            q=q,
            cod_categoria=cod_categoria,
            is_home=is_home,
            limit=limit,
            offset=offset,
        )

    # -------- Create --------
    def create(self, req: CriarVitrineRequest) -> VitrinesModel:
        cat = self.repo.get_categoria_by_id(req.cod_categoria)
        if not cat:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Categoria inválida")

        try:
            return self.repo.create(
                categoria=cat,
                titulo=req.titulo,
                ordem=req.ordem or 1,
                is_home=bool(req.is_home),
            )
        except IntegrityError:
            # slug corrido é tratado no repo; se chegou aqui, é conflito real
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conflito de dados ao criar vitrine")

    # -------- Update --------
    def update(self, vitrine_id: int, req: AtualizarVitrineRequest) -> VitrinesModel:
        v = self.repo.get_vitrine_by_id(vitrine_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")

        cat = None
        if req.cod_categoria is not None:
            cat = self.repo.get_categoria_by_id(req.cod_categoria)
            if not cat:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Categoria inválida")

        try:
            return self.repo.update(
                v,
                categoria=cat,
                titulo=req.titulo,
                ordem=req.ordem,
                is_home=req.is_home,
            )
        except IntegrityError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conflito de dados ao atualizar vitrine")

    # -------- Delete --------
    def delete(self, vitrine_id: int) -> None:
        v = self.repo.get_vitrine_by_id(vitrine_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")

        if self.repo.has_vinculos(vitrine_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir. Existem produtos vinculados."
            )
        self.repo.delete(v)

    # -------- Vínculos produto ↔ vitrine --------
    def vincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        v = self.repo.get_vitrine_by_id(vitrine_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")

        if not self.repo.exists_prod_emp(empresa_id=empresa_id, cod_barras=cod_barras):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto da empresa não encontrado")

        ok = self.repo.vincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Falha ao vincular produto")
        return {"ok": True}

    def desvincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        v = self.repo.get_vitrine_by_id(vitrine_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")

        ok = self.repo.desvincular_produto(vitrine_id=vitrine_id, empresa_id=empresa_id, cod_barras=cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Produto não estava vinculado")
        return {"ok": True}

    # -------- Toggle is_home --------
    def set_is_home(self, vitrine_id: int, is_home: bool) -> VitrinesModel:
        v = self.repo.get_vitrine_by_id(vitrine_id)
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        return self.repo.set_is_home(v, is_home)

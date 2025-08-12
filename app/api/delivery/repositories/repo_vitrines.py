from __future__ import annotations
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from slugify import slugify

from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel

class VitrineRepository:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_categoria_or_400(self, cod_categoria: Optional[int]) -> int:
        if cod_categoria is not None:
            return cod_categoria
        primeira_cat = (
            self.db.query(CategoriaDeliveryModel)
            .order_by(CategoriaDeliveryModel.id.asc())
            .first()
        )
        if not primeira_cat:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Não foi possível criar/atualizar a vitrine: nenhuma categoria cadastrada."
            )
        return primeira_cat.id

    def create(self, cod_categoria: Optional[int], titulo: str, ordem: int = 1, is_home: bool = False) -> VitrinesModel:
        cod_categoria = self._resolve_categoria_or_400(cod_categoria)
        slug_value = slugify(titulo)
        nova = VitrinesModel(
            cod_categoria=cod_categoria,
            titulo=titulo,
            slug=slug_value,
            ordem=ordem,
            tipo_exibicao=("P" if is_home else None),
        )
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar Vitrine")

    def update(
        self,
        vitrine_id: int,
        *,
        cod_categoria: Optional[int] = None,
        titulo: Optional[str] = None,
        ordem: Optional[int] = None,
        is_home: Optional[bool] = None,
    ) -> VitrinesModel:
        v = self.db.query(VitrinesModel).filter_by(id=vitrine_id).first()
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vitrine não encontrada")

        if cod_categoria is not None or cod_categoria is None:
            # só aplica se explicitamente enviado; se None, tenta fallback
            if cod_categoria is None:
                v.cod_categoria = self._resolve_categoria_or_400(None)
            else:
                v.cod_categoria = cod_categoria

        if titulo is not None:
            v.titulo = titulo
            v.slug = slugify(titulo)

        if ordem is not None:
            v.ordem = ordem

        if is_home is not None:
            v.tipo_exibicao = "P" if is_home else None

        try:
            self.db.commit()
            self.db.refresh(v)
            return v
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao atualizar Vitrine")

    def delete(self, vitrine_id: int):
        sub = self.db.query(VitrinesModel).filter_by(id=vitrine_id).first()
        if not sub:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vitrine não encontrada")
        vinculado = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter(ProdutoEmpDeliveryModel.vitrine_id == vitrine_id)
            .first()
        )
        if vinculado:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível excluir. Existem produtos vinculados.")
        self.db.delete(sub)
        self.db.commit()

    # --- Vinculação de produtos ---
    def vincular_produto(self, empresa_id: int, cod_barras: str, vitrine_id: int) -> bool:
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        if not pe:
            return False
        pe.vitrine_id = vitrine_id
        self.db.commit()
        return True

    def desvincular_produto(self, empresa_id: int, cod_barras: str) -> bool:
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        if not pe:
            return False
        pe.vitrine_id = None
        self.db.commit()
        return True

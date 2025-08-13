# app/api/delivery/repositories/repo_vitrines.py
from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from slugify import slugify

from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel
from app.api.mensura.models.association_tables import VitrineProdutoEmpLink


class VitrineRepository:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_categoria_or_400(self, cod_categoria: Optional[int]) -> CategoriaDeliveryModel:
        if cod_categoria is not None:
            cat = self.db.query(CategoriaDeliveryModel).filter_by(id=cod_categoria).first()
            if not cat:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Categoria inválida")
            return cat
        primeira_cat = self.db.query(CategoriaDeliveryModel).order_by(CategoriaDeliveryModel.id.asc()).first()
        if not primeira_cat:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhuma categoria cadastrada.")
        return primeira_cat

    def create(self, cod_categoria: Optional[int], titulo: str, ordem: int = 1, is_home: bool = False) -> VitrinesModel:
        slug_value = slugify(titulo)
        nova = VitrinesModel(
            titulo=titulo,
            slug=slug_value,
            ordem=ordem,
            tipo_exibicao=("P" if is_home else None),
        )
        cat = self._resolve_categoria_or_400(cod_categoria)
        nova.categorias.append(cat)  # 👈 vincula a categoria “principal” para compatibilidade

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

        if cod_categoria is not None:
            cat = self._resolve_categoria_or_400(cod_categoria)
            if cat not in v.categorias:
                v.categorias.append(cat)  # 👈 adiciona sem remover outras (compat mínima)

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
        v = self.db.query(VitrinesModel).filter_by(id=vitrine_id).first()
        if not v:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vitrine não encontrada")
        # verifica se há produtos vinculados via N:N
        vinculado = (
            self.db.query(VitrineProdutoEmpLink)
            .filter(VitrineProdutoEmpLink.vitrine_id == vitrine_id)
            .first()
        )
        if vinculado:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível excluir. Existem produtos vinculados.")
        self.db.delete(v)
        self.db.commit()

    # --- Vinculação de produtos (N:N) ---
    def vincular_produto(self, empresa_id: int, cod_barras: str, vitrine_id: int) -> bool:
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        v = self.db.query(VitrinesModel).filter_by(id=vitrine_id).first()
        if not pe or not v:
            return False
        if v not in pe.vitrines:
            pe.vitrines.append(v)
        self.db.commit()
        return True

    def desvincular_produto(self, empresa_id: int, cod_barras: str, vitrine_id: int) -> bool:
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        if not pe:
            return False
        pe.vitrines = [vt for vt in pe.vitrines if vt.id != vitrine_id]
        self.db.commit()
        return True

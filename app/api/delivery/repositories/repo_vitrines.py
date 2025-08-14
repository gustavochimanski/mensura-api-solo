from __future__ import annotations
from typing import Optional
from slugify import slugify

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel
from app.api.mensura.models.association_tables import VitrineProdutoEmpLink


class VitrineRepository:
    """
    Regra: cada vitrine deve ter exatamente 1 categoria principal.
    O model expõe uma relação M:N (`v.categorias`), mas aqui garantimos 1:1 lógico:
    - create: exige cod_categoria e vincula somente ela
    - update: se vier cod_categoria, limpa e reatribui somente ela
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------- helpers ----------
    def _get_categoria_or_400(self, cod_categoria: int) -> CategoriaDeliveryModel:
        cat = (
            self.db.query(CategoriaDeliveryModel)
            .filter(CategoriaDeliveryModel.id == cod_categoria)
            .first()
        )
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoria inválida")
        return cat

    def _get_vitrine_or_404(self, vitrine_id: int) -> VitrinesModel:
        v = (
            self.db.query(VitrinesModel)
            .options(selectinload(VitrinesModel.categorias))
            .filter(VitrinesModel.id == vitrine_id)
            .first()
        )
        if not v:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitrine não encontrada")
        return v

    def _ensure_unique_slug(self, base: str) -> str:
        """
        Garante slug único adicionando sufixos -2, -3... se necessário.
        Evita erro 500 por unique constraint no banco.
        """
        s = slugify(base)
        if not s:
            s = "vitrine"

        # Busca colisões
        exists = (
            self.db.query(VitrinesModel)
            .filter(VitrinesModel.slug.like(f"{s}%"))
            .all()
        )
        if not exists:
            return s

        # calcula próximo sufixo
        used = {v.slug for v in exists}
        if s not in used:
            return s

        i = 2
        while f"{s}-{i}" in used:
            i += 1
        return f"{s}-{i}"

    def _assign_single_category(self, v: VitrinesModel, cat: CategoriaDeliveryModel) -> None:
        v.categorias.clear()
        v.categorias.append(cat)

    # ---------- CRUD ----------
    def create(self, *, cod_categoria: int, titulo: str, ordem: int = 1, is_home: bool = False) -> VitrinesModel:
        cat = self._get_categoria_or_400(cod_categoria)
        slug_value = self._ensure_unique_slug(titulo)

        nova = VitrinesModel(
            titulo=titulo,
            slug=slug_value,
            ordem=ordem,
            tipo_exibicao=("P" if is_home else None),
        )
        self._assign_single_category(nova, cat)

        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except IntegrityError:
            self.db.rollback()
            # Em caso de corrida de slug, tenta 1x com novo slug
            nova.slug = self._ensure_unique_slug(titulo)
            self.db.add(nova)
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except Exception:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao criar Vitrine")

    def update(
        self,
        vitrine_id: int,
        *,
        cod_categoria: Optional[int] = None,
        titulo: Optional[str] = None,
        ordem: Optional[int] = None,
        is_home: Optional[bool] = None,
    ) -> VitrinesModel:
        v = self._get_vitrine_or_404(vitrine_id)

        if cod_categoria is not None:
            cat = self._get_categoria_or_400(cod_categoria)
            self._assign_single_category(v, cat)

        if titulo is not None:
            v.titulo = titulo
            v.slug = self._ensure_unique_slug(titulo)

        if ordem is not None:
            v.ordem = ordem

        if is_home is not None:
            v.tipo_exibicao = "P" if is_home else None

        try:
            self.db.commit()
            self.db.refresh(v)
            return v
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conflito de dados ao atualizar Vitrine")
        except Exception:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar Vitrine")

    def delete(self, vitrine_id: int) -> None:
        v = self._get_vitrine_or_404(vitrine_id)

        vinculado = (
            self.db.query(VitrineProdutoEmpLink)
            .filter(VitrineProdutoEmpLink.vitrine_id == vitrine_id)
            .first()
        )
        if vinculado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir. Existem produtos vinculados."
            )

        self.db.delete(v)
        self.db.commit()

    # ---------- vínculos produto x vitrine ----------
    def vincular_produto(self, *, empresa_id: int, cod_barras: str, vitrine_id: int) -> bool:
        # valida existência
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoEmpDeliveryModel.cod_barras == cod_barras,
            )
            .first()
        )
        self._get_vitrine_or_404(vitrine_id)
        if not pe:
            return False

        existe = (
            self.db.query(VitrineProdutoEmpLink)
            .filter(
                VitrineProdutoEmpLink.vitrine_id == vitrine_id,
                VitrineProdutoEmpLink.empresa_id == empresa_id,
                VitrineProdutoEmpLink.cod_barras == cod_barras,
            )
            .first()
        )
        if existe:
            return True

        link = VitrineProdutoEmpLink(
            vitrine_id=vitrine_id,
            empresa_id=empresa_id,
            cod_barras=cod_barras,
        )
        self.db.add(link)
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def desvincular_produto(self, *, empresa_id: int, cod_barras: str, vitrine_id: int) -> bool:
        deleted = (
            self.db.query(VitrineProdutoEmpLink)
            .filter(
                VitrineProdutoEmpLink.vitrine_id == vitrine_id,
                VitrineProdutoEmpLink.empresa_id == empresa_id,
                VitrineProdutoEmpLink.cod_barras == cod_barras,
            )
            .delete(synchronize_session=False)
        )
        if deleted == 0:
            self.db.rollback()
            return False
        self.db.commit()
        return True

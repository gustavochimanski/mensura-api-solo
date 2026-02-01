from __future__ import annotations

from typing import Optional, List
from slugify import slugify

from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.cardapio.models.model_vitrine import VitrinesLandingpageStoreModel
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.cadastros.models.association_tables import (
    VitrineLandingProdutoLink,
    VitrineLandingComboLink,
    VitrineLandingReceitaLink,
)


class VitrineLandingpageStoreRepository:
    """
    Repositório (landingpage_store): CRUD/queries no banco.
    - Não lança HTTPException.
    """

    def __init__(self, db: Session):
        self.db = db

    # --------------------- LOOKUPS ---------------------
    def get_vitrine_by_id(
        self, vitrine_id: int, *, empresa_id: Optional[int] = None
    ) -> Optional[VitrinesLandingpageStoreModel]:
        qy = self.db.query(VitrinesLandingpageStoreModel).filter(VitrinesLandingpageStoreModel.id == vitrine_id)
        if empresa_id is not None:
            qy = qy.filter(VitrinesLandingpageStoreModel.empresa_id == empresa_id)
        return qy.first()

    def has_vinculos(self, vitrine_id: int) -> bool:
        return (
            self.db.query(VitrineLandingProdutoLink)
            .filter(VitrineLandingProdutoLink.vitrine_id == vitrine_id)
            .first()
            is not None
        )

    def exists_prod_emp(self, empresa_id: int, cod_barras: str) -> bool:
        return (
            self.db.query(ProdutoEmpModel)
            .filter(
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.cod_barras == cod_barras,
            )
            .first()
            is not None
        )

    # --------------------- SEARCH ---------------------
    def _has_unaccent(self) -> bool:
        try:
            row = self.db.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = :name LIMIT 1"),
                {"name": "unaccent"},
            ).first()
            return row is not None
        except Exception:
            return False

    def search(
        self,
        *,
        empresa_id: Optional[int] = None,
        q: Optional[str] = None,
        is_home: Optional[bool] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> List[VitrinesLandingpageStoreModel]:
        if q is not None:
            q = q.strip()[:128]

        qy = (
            self.db.query(VitrinesLandingpageStoreModel)
            .order_by(VitrinesLandingpageStoreModel.ordem, VitrinesLandingpageStoreModel.id)
        )

        if empresa_id is not None:
            qy = qy.filter(VitrinesLandingpageStoreModel.empresa_id == empresa_id)

        if is_home is not None:
            qy = qy.filter(VitrinesLandingpageStoreModel.tipo_exibicao == "P") if is_home \
                else qy.filter(VitrinesLandingpageStoreModel.tipo_exibicao.is_(None))

        if q:
            term = f"%{q}%"
            if self._has_unaccent():
                cond = or_(
                    func.unaccent(VitrinesLandingpageStoreModel.titulo).ilike(func.unaccent(term)),
                    func.unaccent(VitrinesLandingpageStoreModel.slug).ilike(func.unaccent(term)),
                )
            else:
                cond = or_(
                    VitrinesLandingpageStoreModel.titulo.ilike(term),
                    VitrinesLandingpageStoreModel.slug.ilike(term),
                )
            qy = qy.filter(cond)

        return qy.offset(offset).limit(limit).all()

    # --------------------- HELPERS ---------------------
    def _ensure_unique_slug(self, base: str, *, empresa_id: Optional[int]) -> str:
        s = slugify(base) or "vitrine"
        qy = self.db.query(VitrinesLandingpageStoreModel.slug).filter(VitrinesLandingpageStoreModel.slug.like(f"{s}%"))
        if empresa_id is not None:
            qy = qy.filter(VitrinesLandingpageStoreModel.empresa_id == empresa_id)
        rows = qy.all()
        if not rows:
            return s
        used = {r[0] for r in rows}
        if s not in used:
            return s
        i = 2
        while f"{s}-{i}" in used:
            i += 1
        return f"{s}-{i}"

    def _get_next_ordem(self, *, empresa_id: Optional[int]) -> int:
        qy = self.db.query(func.max(VitrinesLandingpageStoreModel.ordem))
        if empresa_id is not None:
            qy = qy.filter(VitrinesLandingpageStoreModel.empresa_id == empresa_id)
        max_ordem = qy.scalar()
        return (max_ordem or 0) + 1

    # --------------------- CRUD ---------------------
    def create(
        self,
        *,
        empresa_id: int,
        titulo: str,
        is_home: bool = False,
    ) -> VitrinesLandingpageStoreModel:
        ordem = self._get_next_ordem(empresa_id=empresa_id)
        nova = VitrinesLandingpageStoreModel(
            empresa_id=empresa_id,
            titulo=titulo,
            slug=self._ensure_unique_slug(titulo, empresa_id=empresa_id),
            ordem=ordem,
            tipo_exibicao=("P" if is_home else None),
        )
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except IntegrityError:
            self.db.rollback()
            nova.slug = self._ensure_unique_slug(titulo, empresa_id=empresa_id)
            self.db.add(nova)
            self.db.commit()
            self.db.refresh(nova)
            return nova

    def update(
        self,
        vitrine: VitrinesLandingpageStoreModel,
        *,
        titulo: Optional[str] = None,
        ordem: Optional[int] = None,
        is_home: Optional[bool] = None,
    ) -> VitrinesLandingpageStoreModel:
        if titulo is not None:
            vitrine.titulo = titulo
            vitrine.slug = self._ensure_unique_slug(titulo, empresa_id=vitrine.empresa_id)
        if ordem is not None:
            vitrine.ordem = ordem
        if is_home is not None:
            vitrine.tipo_exibicao = "P" if is_home else None

        self.db.commit()
        self.db.refresh(vitrine)
        return vitrine

    def delete(self, vitrine: VitrinesLandingpageStoreModel) -> None:
        self.db.delete(vitrine)
        self.db.commit()

    def set_is_home(self, vitrine: VitrinesLandingpageStoreModel, is_home: bool) -> VitrinesLandingpageStoreModel:
        vitrine.tipo_exibicao = "P" if is_home else None
        self.db.commit()
        self.db.refresh(vitrine)
        return vitrine

    # --------------------- VÍNCULOS PRODUTO ↔ VITRINE ---------------------
    def vincular_produto(self, *, vitrine_id: int, cod_barras: str) -> bool:
        produto_id = (
            self.db.query(ProdutoModel.id)
            .filter(ProdutoModel.cod_barras == cod_barras)
            .scalar()
        )
        if not produto_id:
            return False

        exists = (
            self.db.query(VitrineLandingProdutoLink)
            .filter(
                VitrineLandingProdutoLink.vitrine_id == vitrine_id,
                VitrineLandingProdutoLink.produto_id == produto_id,
            )
            .first()
        )
        if exists:
            return True

        link = VitrineLandingProdutoLink(vitrine_id=vitrine_id, produto_id=produto_id)
        self.db.add(link)
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def desvincular_produto(self, *, vitrine_id: int, cod_barras: str) -> bool:
        produto_id = (
            self.db.query(ProdutoModel.id)
            .filter(ProdutoModel.cod_barras == cod_barras)
            .scalar()
        )
        if not produto_id:
            return False

        deleted = (
            self.db.query(VitrineLandingProdutoLink)
            .filter(
                VitrineLandingProdutoLink.vitrine_id == vitrine_id,
                VitrineLandingProdutoLink.produto_id == produto_id,
            )
            .delete(synchronize_session=False)
        )
        if deleted == 0:
            self.db.rollback()
            return False
        self.db.commit()
        return True

    # --------------------- VÍNCULOS COMBO ↔ VITRINE ---------------------
    def vincular_combo(self, *, vitrine_id: int, combo_id: int) -> bool:
        exists = (
            self.db.query(VitrineLandingComboLink)
            .filter(
                VitrineLandingComboLink.vitrine_id == vitrine_id,
                VitrineLandingComboLink.combo_id == combo_id,
            )
            .first()
        )
        if exists:
            return True

        link = VitrineLandingComboLink(vitrine_id=vitrine_id, combo_id=combo_id)
        self.db.add(link)
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def desvincular_combo(self, *, vitrine_id: int, combo_id: int) -> bool:
        deleted = (
            self.db.query(VitrineLandingComboLink)
            .filter(
                VitrineLandingComboLink.vitrine_id == vitrine_id,
                VitrineLandingComboLink.combo_id == combo_id,
            )
            .delete(synchronize_session=False)
        )
        if deleted == 0:
            self.db.rollback()
            return False
        self.db.commit()
        return True

    # --------------------- VÍNCULOS RECEITA ↔ VITRINE ---------------------
    def vincular_receita(self, *, vitrine_id: int, receita_id: int) -> bool:
        exists = (
            self.db.query(VitrineLandingReceitaLink)
            .filter(
                VitrineLandingReceitaLink.vitrine_id == vitrine_id,
                VitrineLandingReceitaLink.receita_id == receita_id,
            )
            .first()
        )
        if exists:
            return True

        link = VitrineLandingReceitaLink(vitrine_id=vitrine_id, receita_id=receita_id)
        self.db.add(link)
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def desvincular_receita(self, *, vitrine_id: int, receita_id: int) -> bool:
        deleted = (
            self.db.query(VitrineLandingReceitaLink)
            .filter(
                VitrineLandingReceitaLink.vitrine_id == vitrine_id,
                VitrineLandingReceitaLink.receita_id == receita_id,
            )
            .delete(synchronize_session=False)
        )
        if deleted == 0:
            self.db.rollback()
            return False
        self.db.commit()
        return True


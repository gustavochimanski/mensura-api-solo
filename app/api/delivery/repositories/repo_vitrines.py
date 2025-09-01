from __future__ import annotations
from typing import Optional, List
from slugify import slugify

from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.delivery.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.delivery.models.model_vitrine_dv import VitrinesModel
from app.api.mensura.models.association_tables import VitrineProdutoEmpLink, VitrineCategoriaLink


class VitrineRepository:
    """
    Repositório: somente operações de banco (CRUD/queries).
    - Não importa FastAPI nem lança HTTPException.
    - Propaga exceções técnicas (IntegrityError, etc.) para o Service tratar.
    """

    def __init__(self, db: Session):
        self.db = db

    # --------------------- LOOKUPS ---------------------
    def get_vitrine_by_id(self, vitrine_id: int) -> Optional[VitrinesModel]:
        return (
            self.db.query(VitrinesModel)
            .options(
                selectinload(VitrinesModel.categorias)
                .selectinload(CategoriaDeliveryModel.parent)
            )
            .filter(VitrinesModel.id == vitrine_id)
            .first()
        )

    def get_categoria_by_id(self, cat_id: int) -> Optional[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .filter(CategoriaDeliveryModel.id == cat_id)
            .first()
        )

    def has_vinculos(self, vitrine_id: int) -> bool:
        return (
            self.db.query(VitrineProdutoEmpLink)
            .filter(VitrineProdutoEmpLink.vitrine_id == vitrine_id)
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
        q: Optional[str] = None,
        cod_categoria: Optional[int] = None,
        is_home: Optional[bool] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> List[VitrinesModel]:
        # defesa de performance
        if q is not None:
            q = q.strip()[:128]

        qy = (
            self.db.query(VitrinesModel)
            .options(
                selectinload(VitrinesModel.categorias)
                .selectinload(CategoriaDeliveryModel.parent)
            )
            .order_by(VitrinesModel.ordem, VitrinesModel.id)
        )

        if cod_categoria is not None:
            qy = (
                qy.join(VitrineCategoriaLink, VitrineCategoriaLink.vitrine_id == VitrinesModel.id)
                  .filter(VitrineCategoriaLink.categoria_id == cod_categoria)
            )

        if is_home is not None:
            qy = qy.filter(VitrinesModel.tipo_exibicao == "P") if is_home \
                 else qy.filter(VitrinesModel.tipo_exibicao.is_(None))

        if q:
            term = f"%{q}%"
            if self._has_unaccent():
                cond = or_(
                    func.unaccent(VitrinesModel.titulo).ilike(func.unaccent(term)),
                    func.unaccent(VitrinesModel.slug).ilike(func.unaccent(term)),
                )
            else:
                cond = or_(
                    VitrinesModel.titulo.ilike(term),
                    VitrinesModel.slug.ilike(term),
                )
            qy = qy.filter(cond)

        return qy.offset(offset).limit(limit).all()

    # --------------------- HELPERS ---------------------
    def _ensure_unique_slug(self, base: str) -> str:
        s = slugify(base) or "vitrine"
        # like com parâmetro (bound)
        rows = (
            self.db.query(VitrinesModel.slug)
            .filter(VitrinesModel.slug.like(f"{s}%"))
            .all()
        )
        if not rows:
            return s
        used = {r[0] for r in rows}
        if s not in used:
            return s
        i = 2
        while f"{s}-{i}" in used:
            i += 1
        return f"{s}-{i}"

    def _assign_single_category(self, v: VitrinesModel, cat: CategoriaDeliveryModel) -> None:
        v.categorias.clear()
        v.categorias.append(cat)

    # --------------------- CRUD ---------------------
    def create(
        self,
        *,
        categoria: CategoriaDeliveryModel,
        titulo: str,
        ordem: int = 1,
        is_home: bool = False,
    ) -> VitrinesModel:
        nova = VitrinesModel(
            titulo=titulo,
            slug=self._ensure_unique_slug(titulo),
            ordem=ordem,
            tipo_exibicao=("P" if is_home else None),
        )
        self._assign_single_category(nova, categoria)

        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except IntegrityError:
            self.db.rollback()
            # corrida de slug: tenta 1x com novo slug
            nova.slug = self._ensure_unique_slug(titulo)
            self.db.add(nova)
            self.db.commit()
            self.db.refresh(nova)
            return nova

    def update(
        self,
        vitrine: VitrinesModel,
        *,
        categoria: Optional[CategoriaDeliveryModel] = None,
        titulo: Optional[str] = None,
        ordem: Optional[int] = None,
        is_home: Optional[bool] = None,
    ) -> VitrinesModel:
        if categoria is not None:
            self._assign_single_category(vitrine, categoria)
        if titulo is not None:
            vitrine.titulo = titulo
            vitrine.slug = self._ensure_unique_slug(titulo)
        if ordem is not None:
            vitrine.ordem = ordem
        if is_home is not None:
            vitrine.tipo_exibicao = "P" if is_home else None

        self.db.commit()
        self.db.refresh(vitrine)
        return vitrine

    def delete(self, vitrine: VitrinesModel) -> None:
        self.db.delete(vitrine)
        self.db.commit()

    # --------------------- VÍNCULOS PRODUTO ↔ VITRINE ---------------------
    def vincular_produto(self, *, vitrine_id: int, empresa_id: int, cod_barras: str) -> bool:
        # evita duplicidade
        exists = (
            self.db.query(VitrineProdutoEmpLink)
            .filter(
                VitrineProdutoEmpLink.vitrine_id == vitrine_id,
                VitrineProdutoEmpLink.empresa_id == empresa_id,
                VitrineProdutoEmpLink.cod_barras == cod_barras,
            )
            .first()
        )
        if exists:
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

    def desvincular_produto(self, *, vitrine_id: int, empresa_id: int, cod_barras: str) -> bool:
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

    def set_is_home(self, vitrine: VitrinesModel, is_home: bool) -> VitrinesModel:
        vitrine.tipo_exibicao = "P" if is_home else None
        self.db.commit()
        self.db.refresh(vitrine)
        return vitrine

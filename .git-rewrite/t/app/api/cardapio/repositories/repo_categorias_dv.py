from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel


class CategoriaDeliveryDVRepository:
    """Repositório centralizado para operações com categorias do Delivery."""

    def __init__(self, db: Session):
        self.db = db

    def list_by_parent(self, parent_id: Optional[int]) -> List[CategoriaDeliveryModel]:
        query = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .order_by(CategoriaDeliveryModel.posicao)
        )

        if parent_id is None:
            query = query.filter(CategoriaDeliveryModel.parent_id.is_(None))
        else:
            query = query.filter(CategoriaDeliveryModel.parent_id == parent_id)

        return query.all()

    def get_by_id(self, categoria_id: int) -> Optional[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .filter(CategoriaDeliveryModel.id == categoria_id)
            .first()
        )

    def search_all(
        self,
        q: Optional[str],
        *,
        limit: int = 30,
        offset: int = 0,
    ) -> List[CategoriaDeliveryModel]:
        """Busca categorias com suporte a filtro por descrição/slug."""

        query = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .order_by(
                CategoriaDeliveryModel.parent_id.isnot(None),
                CategoriaDeliveryModel.posicao,
            )
        )

        if q:
            term = f"%{q.strip()}%"
            try:
                query = query.filter(
                    or_(
                        func.unaccent(CategoriaDeliveryModel.descricao).ilike(func.unaccent(term)),
                        func.unaccent(CategoriaDeliveryModel.slug).ilike(func.unaccent(term)),
                    )
                )
            except Exception:
                query = query.filter(
                    or_(
                        CategoriaDeliveryModel.descricao.ilike(term),
                        CategoriaDeliveryModel.slug.ilike(term),
                    )
                )

        return query.offset(offset).limit(limit).all()


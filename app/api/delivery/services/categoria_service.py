from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session

from app.api.delivery.repositories.categorias_dv_repo import CategoriaDeliveryRepository
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryIn

class CategoriasService:
    def __init__(self, db: Session):
        self.repo = CategoriaDeliveryRepository(db)

    def create(self, data: CategoriaDeliveryIn):
        return self.repo.create(
            descricao=data.descricao,
            slug=data.slug,
            parent_id=data.parent_id,
            imagem=data.imagem,
            posicao=data.posicao,
            tipo_exibicao=getattr(data, "tipo_exibicao", None),
        )

    def list_all(self):
        return self.repo.list_all()

    def list_by_parent(self, parent_id: Optional[int]):
        return self.repo.list_by_parent(parent_id)

    def update(self, cat_id: int, data: dict):
        return self.repo.update(cat_id, data)

    def delete(self, cat_id: int):
        return self.repo.delete(cat_id)

    def toggle_home(self, cat_id: int, on: bool):
        return self.repo.toggle_home(cat_id, on)

    def move_left(self, cat_id: int):
        return self.repo.move_left(cat_id)

    def move_right(self, cat_id: int):
        return self.repo.move_right(cat_id)

from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session

from app.api.delivery.repositories.categorias_dv_repo import CategoriaDeliveryRepository
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryIn
from app.utils.minio_client import remover_arquivo_minio
from app.utils.logger import logger


class CategoriasService:
    def __init__(self, db: Session):
        self.repo = CategoriaDeliveryRepository(db)

    def create(self, data: CategoriaDeliveryIn):
        return self.repo.create(data)

    def list_all(self):
        return self.repo.list_all()

    def list_by_parent(self, parent_id: Optional[int]):
        return self.repo.list_by_parent(parent_id)

    def update(self, cat_id: int, data: dict):
        return self.repo.update(cat_id, data)

    def delete(self, cat_id: int):
        # 1) pega a categoria pra obter a URL da imagem
        cat = self.repo.get_by_id(cat_id)
        image_url = getattr(cat, "imagem", None)

        # 2) remove no banco
        self.repo.delete(cat_id)

        # 3) tenta remover no MinIO (não quebra se falhar)
        if image_url:
            try:
                remover_arquivo_minio(image_url)
                logger.info(f"[Categorias] Imagem removida do MinIO: {image_url}")
            except Exception as e:
                logger.warning(f"[Categorias] Falha ao remover imagem do MinIO: {e} | url={image_url}")

        # sem retorno (mantém semântica atual do repo.delete)
        return None

    def toggle_home(self, cat_id: int, on: bool):
        return self.repo.toggle_home(cat_id, on)

    def move_left(self, cat_id: int):
        return self.repo.move_left(cat_id)

    def move_right(self, cat_id: int):
        return self.repo.move_right(cat_id)

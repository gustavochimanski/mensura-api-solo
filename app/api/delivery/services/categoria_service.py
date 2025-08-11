# app/api/delivery/services/categorias_dv_service.py
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
        # pega a categoria atual para capturar a URL antiga
        atual = self.repo.get_by_id(cat_id)
        url_antiga = getattr(atual, "imagem", None)

        # aplica update no banco
        atualizado = self.repo.update(cat_id, data)

        # se a imagem foi trocada, remove a antiga no MinIO (best-effort)
        if "imagem" in data and data["imagem"] and data["imagem"] != url_antiga and url_antiga:
            try:
                remover_arquivo_minio(url_antiga)
                logger.info(f"[Categorias] Imagem antiga removida do MinIO: {url_antiga}")
            except Exception as e:
                logger.warning(f"[Categorias] Falha ao remover imagem antiga do MinIO: {e} | url={url_antiga}")

        return atualizado

    def delete(self, cat_id: int):
        # pega a categoria pra obter a URL
        cat = self.repo.get_by_id(cat_id)
        image_url = getattr(cat, "imagem", None)

        # apaga no banco
        self.repo.delete(cat_id)

        # tenta apagar arquivo
        if image_url:
            try:
                remover_arquivo_minio(image_url)
            except Exception as e:
                logger.warning(f"[Categorias] Falha ao remover imagem do MinIO: {e} | url={image_url}")

        return None

    def toggle_home(self, cat_id: int, on: bool):
        return self.repo.toggle_home(cat_id, on)

    def move_left(self, cat_id: int):
        return self.repo.move_left(cat_id)

    def move_right(self, cat_id: int):
        return self.repo.move_right(cat_id)

from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.cardapio.repositories.repo_categoria import CategoriaDeliveryRepository
from app.api.cadastros.schemas.schema_categoria import CategoriaDeliveryIn  # Schema compartilhado
from app.utils.minio_client import remover_arquivo_minio, update_file_to_minio
from app.utils.logger import logger

class CategoriasService:
    def __init__(self, db: Session):
        self.repo = CategoriaDeliveryRepository(db)

    def create(self, data: CategoriaDeliveryIn, *, cod_empresa: int):
        return self.repo.create(data, empresa_id=cod_empresa)

    def list_by_parent(self, parent_id: Optional[int], *, cod_empresa: int):
        return self.repo.list_by_parent(parent_id, empresa_id=cod_empresa)

    def update(self, cat_id: int, data: dict, cod_empresa: int = None, file=None):
        """
        Atualiza categoria com ou sem upload de arquivo.
        Se file for fornecido, faz upload e remove arquivo antigo automaticamente.
        """
        # Se há arquivo, faz upload e remove o antigo
        if file and cod_empresa:
            atual = self.repo.get_by_id(cat_id, empresa_id=cod_empresa)
            url_antiga = getattr(atual, "imagem", None)
            
            nova_url = update_file_to_minio(
                db=self.repo.db,
                cod_empresa=cod_empresa,
                file=file,
                slug="categorias",
                url_antiga=url_antiga
            )
            data["imagem"] = nova_url

        # aplica update no banco
        if not cod_empresa:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "cod_empresa é obrigatório para atualizar categoria")
        return self.repo.update(cat_id, data, empresa_id=cod_empresa)

    def delete(self, cat_id: int, cod_empresa: Optional[int] = None):
        # pega a categoria pra obter a URL
        if not cod_empresa:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "cod_empresa é obrigatório para deletar categoria")
        cat = self.repo.get_by_id(cat_id, empresa_id=cod_empresa)
        image_url = getattr(cat, "imagem", None)

        # apaga no banco
        self.repo.delete(cat_id, empresa_id=cod_empresa)

        # tenta apagar arquivo no MinIO usando o cod_empresa para garantir bucket correto
        if image_url and cod_empresa:
            try:
                remover_arquivo_minio(image_url)
                logger.info(f"[Categorias] Imagem removida do MinIO: {image_url}")
            except Exception as e:
                logger.warning(f"[Categorias] Falha ao remover imagem do MinIO: {e} | url={image_url}")

        return None

    def move_left(self, cat_id: int):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "move_left requer cod_empresa")

    def move_right(self, cat_id: int):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "move_right requer cod_empresa")

    def move_left_empresa(self, cat_id: int, *, cod_empresa: int):
        return self.repo.move_left(cat_id, empresa_id=cod_empresa)

    def move_right_empresa(self, cat_id: int, *, cod_empresa: int):
        return self.repo.move_right(cat_id, empresa_id=cod_empresa)

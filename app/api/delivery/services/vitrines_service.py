from __future__ import annotations
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.vitrines_repo import VitrineRepository
from app.api.delivery.repositories.produtos_dv_repo import ProdutoDeliveryRepository
from app.api.delivery.schemas.vitrine_schema import CriarVitrineRequest

class VitrinesService:
    def __init__(self, db: Session):
        self.repo = VitrineRepository(db)
        self.repo_prod = ProdutoDeliveryRepository(db)

    def listar(self, empresa_id: int, cod_categoria: int | None = None):
        return self.repo.listar(empresa_id, cod_categoria)

    def create(self, req: CriarVitrineRequest):
        return self.repo.create(req.cod_categoria, req.titulo, req.ordem)

    def delete(self, vitrine_id: int):
        return self.repo.delete(vitrine_id)

    def atribuir_produto(self, empresa_id: int, cod_barras: str, vitrine_id: int):
        ok = self.repo.atribuir_produto(empresa_id, cod_barras, vitrine_id)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto da empresa não encontrado")
        return {"ok": True}

    def remover_produto(self, empresa_id: int, cod_barras: str):
        ok = self.repo.remover_produto(empresa_id, cod_barras)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto da empresa não encontrado")
        return {"ok": True}

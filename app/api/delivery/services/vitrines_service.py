from __future__ import annotations
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.repo_vitrines import VitrineRepository
from app.api.delivery.repositories.repo_produtos_dv import ProdutoDeliveryRepository
from app.api.delivery.schemas.vitrine_schema import CriarVitrineRequest, AtualizarVitrineRequest

class VitrinesService:
    def __init__(self, db: Session):
        self.repo = VitrineRepository(db)
        self.repo_prod = ProdutoDeliveryRepository(db)

    def create(self, req: CriarVitrineRequest):
        return self.repo.create(req.cod_categoria, req.titulo, req.ordem, req.is_home)

    def update(self, vitrine_id: int, req: AtualizarVitrineRequest):
        return self.repo.update(
            vitrine_id,
            cod_categoria=req.cod_categoria,
            titulo=req.titulo,
            ordem=req.ordem,
            is_home=req.is_home,
        )

    def delete(self, vitrine_id: int):
        return self.repo.delete(vitrine_id)

    def vincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        ok = self.repo.vincular_produto(empresa_id, cod_barras, vitrine_id)
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto da empresa não encontrado")
        return {"ok": True}

    def desvincular_produto(self, vitrine_id: int, empresa_id: int, cod_barras: str):
        ok = self.repo.desvincular_produto(empresa_id, cod_barras, vitrine_id)  # 👈 passa vitrine_id
        if not ok:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto da empresa não encontrado")
        return {"ok": True}

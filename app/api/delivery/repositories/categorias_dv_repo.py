# app/api/delivery/repositories/categorias_dv_repo.py
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryIn

class CategoriaDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dados: CategoriaDeliveryIn) -> CategoriaDeliveryModel:
        slug_value = dados.slug or dados.descricao.lower().replace(" ", "-")
        existe = (
            self.db.query(CategoriaDeliveryModel)
            .filter_by(slug=slug_value)
            .first()
        )
        if existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com esse slug.",
            )

        if dados.posicao is None:
            max_posicao = (
                self.db.query(func.max(CategoriaDeliveryModel.posicao))
                .filter(CategoriaDeliveryModel.parent_id == dados.parent_id)
                .scalar()
            )
            dados.posicao = (max_posicao or 0) + 1

        nova = CategoriaDeliveryModel(
            descricao=dados.descricao,
            slug=slug_value,
            parent_id=dados.parent_id,
            imagem=dados.imagem,
            posicao=dados.posicao,
        )
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar categoria",
            )

    def list_all(self) -> list[CategoriaDeliveryModel]:
        stmt = select(CategoriaDeliveryModel).order_by(CategoriaDeliveryModel.posicao)
        return self.db.execute(stmt).scalars().all()

    def list_by_parent(self, parent_id: Optional[int]) -> list[CategoriaDeliveryModel]:
        stmt = (
            select(CategoriaDeliveryModel)
            .where(CategoriaDeliveryModel.parent_id == parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
        )
        return self.db.execute(stmt).scalars().all()

    def get_by_id(self, cat_id: int) -> CategoriaDeliveryModel:
        cat = self.db.query(CategoriaDeliveryModel).filter_by(id=cat_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
        return cat

    def update(self, cat_id: int, update_data: dict) -> CategoriaDeliveryModel:
        cat = self.get_by_id(cat_id)
        for key, value in update_data.items():
            if value is not None:
                setattr(cat, key, value)
        try:
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar categoria"
            )

    def delete(self, cat_id: int) -> None:
        cat = self.get_by_id(cat_id)
        self.db.delete(cat)
        self.db.commit()

    def move_right(self, cat_id: int) -> CategoriaDeliveryModel:
        cat = self.get_by_id(cat_id)
        irmas = (
            self.db.query(CategoriaDeliveryModel)
            .filter_by(parent_id=cat.parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )
        idx = next((i for i, c in enumerate(irmas) if c.id == cat_id), None)
        if idx is None or idx == len(irmas) - 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Não é possível mover para a direita")
        proxima = irmas[idx + 1]
        cat.posicao, proxima.posicao = proxima.posicao, cat.posicao
        try:
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao mover categoria para a direita")

    def move_left(self, cat_id: int) -> CategoriaDeliveryModel:
        cat = self.get_by_id(cat_id)
        irmas = (
            self.db.query(CategoriaDeliveryModel)
            .filter_by(parent_id=cat.parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )
        idx = next((i for i, c in enumerate(irmas) if c.id == cat_id), None)
        if idx is None or idx == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Não é possível mover para a esquerda")
        anterior = irmas[idx - 1]
        cat.posicao, anterior.posicao = anterior.posicao, cat.posicao
        try:
            self.db.commit()
            self.db.refresh(cat)
            return cat
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao mover categoria para a esquerda")

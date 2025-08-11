from __future__ import annotations
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from slugify import slugify

from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel

class VitrineRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, cod_empresa: int, cod_categoria: int | None = None) -> List[VitrinesModel]:
        subquery = (
            self.db.query(ProdutoEmpDeliveryModel.vitrine_id)
            .filter(ProdutoEmpDeliveryModel.empresa_id == cod_empresa)
            .distinct()
            .subquery()
        )
        q = self.db.query(VitrinesModel).outerjoin(subquery, VitrinesModel.id == subquery.c.vitrine_id)
        if cod_categoria is not None:
            q = q.filter(VitrinesModel.cod_categoria == cod_categoria)
        return q.order_by(VitrinesModel.ordem).all()

    def create(self, cod_categoria: int, titulo: str, ordem: int = 1) -> VitrinesModel:
        slug_value = slugify(titulo)
        nova = VitrinesModel(cod_categoria=cod_categoria, titulo=titulo, slug=slug_value, ordem=ordem)
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            return nova
        except Exception:
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar Vitrine")

    def delete(self, vitrine_id: int):
        sub = self.db.query(VitrinesModel).filter_by(id=vitrine_id).first()
        if not sub:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vitrine não encontrada")
        vinculado = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter(ProdutoEmpDeliveryModel.vitrine_id == vitrine_id)
            .first()
        )
        if vinculado:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível excluir. Existem produtos vinculados.")
        self.db.delete(sub)
        self.db.commit()

    # --- Vinculação de produtos ---
    def atribuir_produto(self, empresa_id: int, cod_barras: str, vitrine_id: int) -> bool:
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        if not pe:
            return False
        pe.vitrine_id = vitrine_id
        self.db.commit()
        return True

    def remover_produto(self, empresa_id: int, cod_barras: str) -> bool:
        pe = (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        if not pe:
            return False
        pe.vitrine_id = None
        self.db.commit()
        return True

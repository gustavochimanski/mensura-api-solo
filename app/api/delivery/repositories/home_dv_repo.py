from __future__ import annotations
from typing import List, Dict
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel


class HomeRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Categorias ----------
    def listar_categorias(self, only_home: bool = False) -> List[CategoriaDeliveryModel]:
        stmt = (
            select(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .order_by(CategoriaDeliveryModel.posicao)
        )
        cats = self.db.execute(stmt).scalars().all()
        if only_home:
            cats = [c for c in cats if c.is_home]  # usa a property do model
        return cats

    # ---------- Vitrines ----------
    def listar_vitrines_por_categoria(self, cod_categoria: int) -> List[VitrinesModel]:
        return (
            self.db.query(VitrinesModel)
            .filter(VitrinesModel.cod_categoria == cod_categoria)
            .order_by(VitrinesModel.ordem)
            .all()
        )

    def listar_produtos_emp_por_categoria_e_sub(self, empresa_id: int, cod_categoria: int) -> List[ProdutoEmpDeliveryModel]:
        """
        Retorna produtos da empresa que estão na categoria informada ou em suas subcategorias.
        """
        categoria = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.children))
            .filter(CategoriaDeliveryModel.id == cod_categoria)
            .first()
        )

        if not categoria:
            return []

        ids = {categoria.id} | {c.id for c in categoria.children}

        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .join(ProdutoEmpDeliveryModel.produto)
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoEmpDeliveryModel.disponivel.is_(True),
                ProdutoEmpDeliveryModel.produto.has(CategoriaDeliveryModel.id.in_(ids))
            )
            .all()
        )

    def listar_vitrines_com_produtos_empresa_categoria(
        self, empresa_id: int, cod_categoria: int
    ) -> Dict[int, List[ProdutoEmpDeliveryModel]]:
        """
        Dicionário {vitrine_id: [ProdutoEmpDeliveryModel, ...]} filtrando empresa/categoria e somente disponíveis.
        """
        produtos = self.listar_produtos_emp_por_categoria_e_sub(empresa_id, cod_categoria)
        agrupado: Dict[int, List[ProdutoEmpDeliveryModel]] = defaultdict(list)
        for p in produtos:
            if p.vitrine_id is not None:
                agrupado[p.vitrine_id].append(p)
        return agrupado

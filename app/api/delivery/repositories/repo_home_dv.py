from __future__ import annotations
from typing import List, Dict, Optional
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
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
            # somente categorias raiz (sem pai)
            cats = [c for c in cats if not c.parent_id]
        return cats

    # ---------- Vitrines ----------
    def listar_vitrines(self, is_home: Optional[bool] = None) -> List[VitrinesModel]:
        """
        Lista vitrines. Se is_home for:
          - True  -> tipo_exibicao IS NOT NULL (ou == 'P' se preferir)
          - False -> tipo_exibicao IS NULL
          - None  -> sem filtro por home
        """
        q = self.db.query(VitrinesModel).order_by(VitrinesModel.ordem)
        if is_home is True:
            q = q.filter(VitrinesModel.tipo_exibicao.isnot(None))
            # Se a regra for estrita:
            # q = q.filter(VitrinesModel.tipo_exibicao == "P")
        elif is_home is False:
            q = q.filter(VitrinesModel.tipo_exibicao.is_(None))
        return q.all()

    def listar_vitrines_por_categoria(self, cod_categoria: int, is_home: Optional[bool] = None) -> List[VitrinesModel]:
        q = (
            self.db.query(VitrinesModel)
            .filter(VitrinesModel.cod_categoria == cod_categoria)
            .order_by(VitrinesModel.ordem)
        )
        if is_home is True:
            q = q.filter(VitrinesModel.tipo_exibicao.isnot(None))
            # ou: q = q.filter(VitrinesModel.tipo_exibicao == "P")
        elif is_home is False:
            q = q.filter(VitrinesModel.tipo_exibicao.is_(None))
        return q.all()

    # ---------- Produtos ----------
    def listar_produtos_emp_por_categoria_e_sub(
        self, empresa_id: int, cod_categoria: int
    ) -> List[ProdutoEmpDeliveryModel]:
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
                ProdutoEmpDeliveryModel.vitrine_id.isnot(None),
                ProdutoDeliveryModel.cod_categoria.in_(ids),
                ProdutoDeliveryModel.ativo.is_(True),
            )
            .all()
        )

    def listar_vitrines_com_produtos_empresa_categoria(
        self, empresa_id: int, cod_categoria: int
    ) -> Dict[int, List[ProdutoEmpDeliveryModel]]:
        produtos = self.listar_produtos_emp_por_categoria_e_sub(empresa_id, cod_categoria)
        agrupado: Dict[int, List[ProdutoEmpDeliveryModel]] = defaultdict(list)
        for p in produtos:
            if p.vitrine_id is not None:
                agrupado[p.vitrine_id].append(p)
        return agrupado

    def listar_produtos_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ProdutoEmpDeliveryModel]]:
        if not vitrine_ids:
            return {}

        produtos = (
            self.db.query(ProdutoEmpDeliveryModel)
            .join(ProdutoEmpDeliveryModel.produto)
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoEmpDeliveryModel.disponivel.is_(True),
                ProdutoEmpDeliveryModel.vitrine_id.in_(vitrine_ids),
                ProdutoDeliveryModel.ativo.is_(True),
            )
            .all()
        )

        agrupado: Dict[int, List[ProdutoEmpDeliveryModel]] = defaultdict(list)
        for p in produtos:
            if p.vitrine_id is not None:
                agrupado[p.vitrine_id].append(p)
        return agrupado

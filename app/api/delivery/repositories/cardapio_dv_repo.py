from __future__ import annotations
from typing import List, Dict, Optional, Set
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel
from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel


class CardapioRepository:
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
            cats = [c for c in cats if c.is_home]
        return cats

    def _ids_subarvore(self, raiz_id: int) -> Set[int]:
        # coleta id da raiz + filhos diretos (poderia expandir recursivamente se necessário)
        stmt = (
            select(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.children))
            .where(CategoriaDeliveryModel.id == raiz_id)
        )
        raiz = self.db.execute(stmt).scalars().first()
        if not raiz:
            return set()
        ids = {raiz.id}
        ids.update([c.id for c in raiz.children])
        return ids

    # ---------- Vitrines ----------
    def listar_vitrines_por_categoria(self, cod_categoria: int) -> List[VitrinesModel]:
        return (
            self.db.query(VitrinesModel)
            .filter(VitrinesModel.cod_categoria == cod_categoria)
            .order_by(VitrinesModel.ordem)
            .all()
        )

    # ---------- Produtos por empresa/categoria ----------
    def listar_produtos_emp_por_categoria_e_sub(self, empresa_id: int, cod_categoria: int) -> List[ProdutoEmpDeliveryModel]:
        ids = self._ids_subarvore(cod_categoria) or {cod_categoria}
        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .join(ProdutoEmpDeliveryModel.produto)
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoDeliveryModel.cod_categoria.in_(ids),
                ProdutoEmpDeliveryModel.disponivel.is_(True),
                ProdutoDeliveryModel.ativo.is_(True),
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

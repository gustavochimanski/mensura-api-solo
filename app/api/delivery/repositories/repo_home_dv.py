# app/api/delivery/repositories/repo_home_dv.py
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from collections import defaultdict
from typing import List, Dict
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel
from app.api.mensura.models.association_tables import VitrineProdutoEmpLink, VitrineCategoriaLink


class HomeRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_categorias(self, is_home: bool) -> List[CategoriaDeliveryModel]:
        stmt = (
            select(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .order_by(CategoriaDeliveryModel.posicao)
        )
        cats = self.db.execute(stmt).scalars().all()
        if is_home is True:
            cats = [c for c in cats if not c.parent_id]
        return cats

    def listar_vitrines(self, is_home: bool) -> List[VitrinesModel]:
        q = (
            self.db.query(VitrinesModel)
            .options(
                joinedload(VitrinesModel.categorias).joinedload(CategoriaDeliveryModel.parent)  # 👈 carrega N:N
            )
            .order_by(VitrinesModel.ordem)
        )
        if is_home is True:
            q = q.filter(VitrinesModel.tipo_exibicao.isnot(None))
        elif is_home is False:
            q = q.filter(VitrinesModel.tipo_exibicao.is_(None))
        return q.all()

    def listar_vitrines_por_categoria(self, cod_categoria: int, is_home: bool) -> List[VitrinesModel]:
        q = (
            self.db.query(VitrinesModel)
            .join(VitrineCategoriaLink, VitrineCategoriaLink.vitrine_id == VitrinesModel.id)
            .filter(VitrineCategoriaLink.categoria_id == cod_categoria)
            .options(
                joinedload(VitrinesModel.categorias).joinedload(CategoriaDeliveryModel.parent)
            )
            .order_by(VitrinesModel.ordem)
        )
        if is_home is True:
            q = q.filter(VitrinesModel.tipo_exibicao.isnot(None))
        elif is_home is False:
            q = q.filter(VitrinesModel.tipo_exibicao.is_(None))
        return q.all()

    def listar_vitrines_com_produtos_empresa_categoria(self, empresa_id: int, cod_categoria: int) -> Dict[int, List[ProdutoEmpDeliveryModel]]:
        # produtos da empresa, ativos, com categoria (incluindo filhos), e com vínculo em QUALQUER vitrine
        categoria = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.children))
            .filter(CategoriaDeliveryModel.id == cod_categoria)
            .first()
        )
        if not categoria:
            return {}
        ids = {categoria.id} | {c.id for c in categoria.children}

        rows = (
            self.db.query(ProdutoEmpDeliveryModel, VitrineProdutoEmpLink.vitrine_id)
            .join(ProdutoEmpDeliveryModel.produto)
            .join(VitrineProdutoEmpLink, (VitrineProdutoEmpLink.empresa_id == ProdutoEmpDeliveryModel.empresa_id) &
                                         (VitrineProdutoEmpLink.cod_barras == ProdutoEmpDeliveryModel.cod_barras))
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoEmpDeliveryModel.disponivel.is_(True),
                ProdutoDeliveryModel.ativo.is_(True),
                ProdutoDeliveryModel.cod_categoria.in_(ids),
            )
            .all()
        )
        out: Dict[int, List[ProdutoEmpDeliveryModel]] = defaultdict(list)
        for pe, vid in rows:
            out[vid].append(pe)
        return out

    def listar_produtos_por_vitrine_ids(self, empresa_id: int, vitrine_ids: List[int]) -> Dict[int, List[ProdutoEmpDeliveryModel]]:
        if not vitrine_ids:
            return {}
        rows = (
            self.db.query(ProdutoEmpDeliveryModel, VitrineProdutoEmpLink.vitrine_id)
            .join(ProdutoEmpDeliveryModel.produto)
            .join(VitrineProdutoEmpLink, (VitrineProdutoEmpLink.empresa_id == ProdutoEmpDeliveryModel.empresa_id) &
                                         (VitrineProdutoEmpLink.cod_barras == ProdutoEmpDeliveryModel.cod_barras))
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa_id == empresa_id,
                ProdutoEmpDeliveryModel.disponivel.is_(True),
                ProdutoDeliveryModel.ativo.is_(True),
                VitrineProdutoEmpLink.vitrine_id.in_(vitrine_ids),
            )
            .all()
        )
        out: Dict[int, List[ProdutoEmpDeliveryModel]] = defaultdict(list)
        for pe, vid in rows:
            out[vid].append(pe)
        return out

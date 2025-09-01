from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.api.delivery.models.model_vitrine_dv import VitrinesModel
from app.api.delivery.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.mensura.models.association_tables import (
    VitrineCategoriaLink,
    VitrineProdutoEmpLink,
)


class HomeRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----------------- Categorias -----------------
    def listar_categorias(self, is_home: bool) -> List[CategoriaDeliveryModel]:
        """
        is_home=True  -> apenas categorias raiz (parent_id IS NULL)
        is_home=False -> todas as categorias
        """
        q = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .order_by(CategoriaDeliveryModel.posicao)
        )
        if is_home:
            q = q.filter(CategoriaDeliveryModel.parent_id.is_(None))
        return q.all()

    # ----------------- Vitrines (geral) -----------------
    def listar_vitrines(self, is_home: bool) -> List[VitrinesModel]:
        q = (
            self.db.query(VitrinesModel)
            .options(
                joinedload(VitrinesModel.categorias)
                .joinedload(CategoriaDeliveryModel.parent)
            )
            .order_by(VitrinesModel.ordem)
        )
        if is_home:
            q = q.filter(VitrinesModel.tipo_exibicao == "P")
        return q.all()

    # ----------------- Vitrines por categoria -----------------
    def listar_vitrines_por_categoria(self, categoria_id: int) -> List[VitrinesModel]:
        """
        Busca vitrines ligadas à categoria via tabela de associação.
        (Sem filtro de 'home')
        """
        q = (
            self.db.query(VitrinesModel)
            .join(VitrineCategoriaLink, VitrineCategoriaLink.vitrine_id == VitrinesModel.id)
            .filter(VitrineCategoriaLink.categoria_id == categoria_id)
            .options(
                joinedload(VitrinesModel.categorias)
                .joinedload(CategoriaDeliveryModel.parent)
            )
            .order_by(VitrineCategoriaLink.posicao, VitrinesModel.ordem)
        )
        return q.all()

    # ----------------- Produtos por vitrine (lista de IDs) -----------------
    def listar_produtos_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ProdutoEmpModel]]:
        """
        Retorna {vitrine_id: [ProdutoEmpDeliveryModel,...]} apenas dos vínculos (empresa_id,cod_barras) na vitrine,
        já com Produto carregado. Filtra por disponibilidade.
        """
        if not vitrine_ids:
            return {}

        rows: List[Tuple[int, ProdutoEmpModel]] = (
            self.db.query(VitrineProdutoEmpLink.vitrine_id, ProdutoEmpModel)
            .join(
                ProdutoEmpModel,
                and_(
                    ProdutoEmpModel.empresa_id == VitrineProdutoEmpLink.empresa_id,
                    ProdutoEmpModel.cod_barras == VitrineProdutoEmpLink.cod_barras,
                ),
            )
            .filter(
                VitrineProdutoEmpLink.vitrine_id.in_(vitrine_ids),
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.disponivel.is_(True),
            )
            .options(joinedload(ProdutoEmpModel.produto))
            .order_by(VitrineProdutoEmpLink.posicao)
            .all()
        )

        out: Dict[int, List[ProdutoEmpModel]] = {}
        for vit_id, prod_emp in rows:
            out.setdefault(vit_id, []).append(prod_emp)
        return out

    # ----------------- Produtos por (empresa, categoria) -----------------
    def listar_vitrines_com_produtos_empresa_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> Dict[int, List[ProdutoEmpModel]]:
        """
        Mesmo formato do método acima, mas restringe as vitrines à categoria informada
        (via vitrine_categoria_dv) — evita trazer produtos de vitrines não relacionadas.
        """
        rows: List[Tuple[int, ProdutoEmpModel]] = (
            self.db.query(VitrineProdutoEmpLink.vitrine_id, ProdutoEmpModel)
            .join(
                ProdutoEmpModel,
                and_(
                    ProdutoEmpModel.empresa_id == VitrineProdutoEmpLink.empresa_id,
                    ProdutoEmpModel.cod_barras == VitrineProdutoEmpLink.cod_barras,
                ),
            )
            .join(
                VitrineCategoriaLink,
                VitrineCategoriaLink.vitrine_id == VitrineProdutoEmpLink.vitrine_id,
            )
            .filter(
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.disponivel.is_(True),
                VitrineCategoriaLink.categoria_id == categoria_id,
            )
            .options(joinedload(ProdutoEmpModel.produto))
            .order_by(VitrineProdutoEmpLink.posicao)
            .all()
        )

        out: Dict[int, List[ProdutoEmpModel]] = {}
        for vit_id, prod_emp in rows:
            out.setdefault(vit_id, []).append(prod_emp)
        return out


    # 🆕 Busca categoria por slug
    def get_categoria_by_slug(self, slug: str) -> Optional[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .filter(CategoriaDeliveryModel.slug == slug)
            .first()
        )

    # 🆕 Lista subcategorias de um pai
    def listar_subcategorias(self, parent_id: int) -> List[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .filter(CategoriaDeliveryModel.parent_id == parent_id)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )

    def listar_primeiras_vitrines_por_categorias(
            self, categoria_ids: List[int]
    ) -> Dict[int, VitrinesModel]:
        """
        Retorna um dict {categoria_id: VitrinesModel} contendo a vitrine de menor `ordem`
        para cada categoria em `categoria_ids`.
        """
        if not categoria_ids:
            return {}

        out: Dict[int, VitrinesModel] = {}

        for cat_id in categoria_ids:
            vit = (
                self.db.query(VitrinesModel)
                .join(VitrineCategoriaLink, VitrineCategoriaLink.vitrine_id == VitrinesModel.id)
                .filter(VitrineCategoriaLink.categoria_id == cat_id)
                .options(
                    joinedload(VitrinesModel.categorias)
                    .joinedload(CategoriaDeliveryModel.parent)
                )
                .order_by(VitrinesModel.ordem.asc())  # aqui usamos ordem, não posicao
                .first()  # pega só a primeira vitrine
            )
            if vit:
                out[cat_id] = vit

        return out

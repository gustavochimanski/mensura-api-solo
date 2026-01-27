from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_

from app.api.cardapio.models.model_vitrine import VitrinesModel
from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.cadastros.models.association_tables import (
    VitrineCategoriaLink,
    VitrineProdutoLink,
    VitrineComboLink,
    VitrineReceitaLink,
)
from app.api.catalogo.models.model_combo import ComboModel


class HomeRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----------------- Categorias -----------------
    def listar_categorias(self, *, empresa_id: int, is_home: bool) -> List[CategoriaDeliveryModel]:
        """
        is_home=True  -> apenas categorias raiz (parent_id IS NULL)
        is_home=False -> todas as categorias
        """
        q = (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .filter(CategoriaDeliveryModel.empresa_id == empresa_id)
            .order_by(CategoriaDeliveryModel.posicao)
        )
        if is_home:
            q = q.filter(CategoriaDeliveryModel.parent_id.is_(None))
        return q.all()

    # ----------------- Vitrines (geral) -----------------
    def listar_vitrines(self, *, empresa_id: int, is_home: bool) -> List[VitrinesModel]:
        q = (
            self.db.query(VitrinesModel)
            .options(
                joinedload(VitrinesModel.categorias)
                .joinedload(CategoriaDeliveryModel.parent)
            )
            .filter(VitrinesModel.empresa_id == empresa_id)
            .order_by(VitrinesModel.ordem)
        )
        if is_home:
            q = q.filter(VitrinesModel.tipo_exibicao == "P")
        return q.all()

    # ----------------- Vitrines por categoria -----------------
    def listar_vitrines_por_categoria(self, *, empresa_id: int, categoria_id: int) -> List[VitrinesModel]:
        """
        Busca vitrines ligadas à categoria via tabela de associação.
        (Sem filtro de 'home')
        """
        q = (
            self.db.query(VitrinesModel)
            .join(VitrineCategoriaLink, VitrineCategoriaLink.vitrine_id == VitrinesModel.id)
            .filter(VitrineCategoriaLink.categoria_id == categoria_id)
            .filter(VitrinesModel.empresa_id == empresa_id)
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
        Retorna {vitrine_id: [ProdutoEmpDeliveryModel,...]} dos produtos na vitrine,
        já com Produto carregado. Filtra por disponibilidade e empresa.
        Vitrines agora são globais, mas ainda filtramos produtos por empresa.
        """
        if not vitrine_ids:
            return {}

        rows: List[Tuple[int, ProdutoEmpModel]] = (
            self.db.query(VitrineProdutoLink.vitrine_id, ProdutoEmpModel)
            .join(
                VitrinesModel,
                VitrinesModel.id == VitrineProdutoLink.vitrine_id,
            )
            .join(
                ProdutoModel,
                ProdutoModel.cod_barras == VitrineProdutoLink.cod_barras,
            )
            .join(
                ProdutoEmpModel,
                and_(
                    ProdutoEmpModel.cod_barras == ProdutoModel.cod_barras,
                    ProdutoEmpModel.empresa_id == empresa_id,
                ),
            )
            .filter(
                VitrineProdutoLink.vitrine_id.in_(vitrine_ids),
                VitrinesModel.empresa_id == empresa_id,
                ProdutoEmpModel.disponivel.is_(True),
                ProdutoEmpModel.preco_venda > 0,
            )
            .options(
                joinedload(ProdutoEmpModel.produto).selectinload(ProdutoModel.complementos)
            )
            .order_by(VitrineProdutoLink.posicao)
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
        Vitrines agora são globais, mas ainda filtramos produtos por empresa.
        """
        rows: List[Tuple[int, ProdutoEmpModel]] = (
            self.db.query(VitrineProdutoLink.vitrine_id, ProdutoEmpModel)
            .join(
                VitrinesModel,
                VitrinesModel.id == VitrineProdutoLink.vitrine_id,
            )
            .join(
                ProdutoModel,
                ProdutoModel.cod_barras == VitrineProdutoLink.cod_barras,
            )
            .join(
                ProdutoEmpModel,
                and_(
                    ProdutoEmpModel.cod_barras == ProdutoModel.cod_barras,
                    ProdutoEmpModel.empresa_id == empresa_id,
                ),
            )
            .join(
                VitrineCategoriaLink,
                VitrineCategoriaLink.vitrine_id == VitrineProdutoLink.vitrine_id,
            )
            .filter(
                VitrinesModel.empresa_id == empresa_id,
                ProdutoEmpModel.disponivel.is_(True),
                ProdutoEmpModel.preco_venda > 0,
                VitrineCategoriaLink.categoria_id == categoria_id,
            )
            .options(
                joinedload(ProdutoEmpModel.produto).selectinload(ProdutoModel.complementos)
            )
            .order_by(VitrineProdutoLink.posicao)
            .all()
        )

        out: Dict[int, List[ProdutoEmpModel]] = {}
        for vit_id, prod_emp in rows:
            out.setdefault(vit_id, []).append(prod_emp)
        return out


    # 🆕 Busca categoria por slug
    def get_categoria_by_slug(self, *, empresa_id: int, slug: str) -> Optional[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .filter(
                CategoriaDeliveryModel.empresa_id == empresa_id,
                CategoriaDeliveryModel.slug == slug,
            )
            .first()
        )

    # 🆕 Lista subcategorias de um pai
    def listar_subcategorias(self, *, empresa_id: int, parent_id: int) -> List[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .options(joinedload(CategoriaDeliveryModel.parent))
            .filter(
                CategoriaDeliveryModel.empresa_id == empresa_id,
                CategoriaDeliveryModel.parent_id == parent_id,
            )
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )

    def listar_primeiras_vitrines_por_categorias(
            self, *, empresa_id: int, categoria_ids: List[int]
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
                .filter(
                    VitrineCategoriaLink.categoria_id == cat_id,
                    VitrinesModel.empresa_id == empresa_id,
                )
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

    # ----------------- Combos por vitrine (lista de IDs) -----------------
    def listar_combos_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ComboModel]]:
        """
        Retorna {vitrine_id: [ComboModel,...]} apenas dos combos vinculados à vitrine.
        Filtra por empresa e ativo.
        """
        if not vitrine_ids:
            return {}

        rows: List[Tuple[int, ComboModel]] = (
            self.db.query(VitrineComboLink.vitrine_id, ComboModel)
            .join(
                VitrinesModel,
                VitrinesModel.id == VitrineComboLink.vitrine_id,
            )
            .join(
                ComboModel,
                ComboModel.id == VitrineComboLink.combo_id,
            )
            .filter(
                VitrineComboLink.vitrine_id.in_(vitrine_ids),
                VitrinesModel.empresa_id == empresa_id,
                ComboModel.empresa_id == empresa_id,
                ComboModel.ativo.is_(True),
            )
            .options(joinedload(ComboModel.itens))
            .order_by(VitrineComboLink.posicao)
            .all()
        )

        out: Dict[int, List[ComboModel]] = {}
        for vit_id, combo in rows:
            out.setdefault(vit_id, []).append(combo)
        return out

    # ----------------- Receitas por vitrine (lista de IDs) -----------------
    def listar_receitas_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List]:
        """
        Retorna {vitrine_id: [ReceitaModel,...]} apenas das receitas vinculadas à vitrine.
        Receitas estão no schema cadastros.
        Filtra por disponibilidade e empresa.
        """
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        if not vitrine_ids:
            return {}

        rows: List[Tuple[int, ReceitaModel]] = (
            self.db.query(VitrineReceitaLink.vitrine_id, ReceitaModel)
            .join(
                VitrinesModel,
                VitrinesModel.id == VitrineReceitaLink.vitrine_id,
            )
            .join(
                ReceitaModel,
                ReceitaModel.id == VitrineReceitaLink.receita_id,
            )
            .filter(
                VitrineReceitaLink.vitrine_id.in_(vitrine_ids),
                VitrinesModel.empresa_id == empresa_id,
                ReceitaModel.empresa_id == empresa_id,
                ReceitaModel.disponivel.is_(True),
                ReceitaModel.ativo.is_(True),
            )
            .order_by(VitrineReceitaLink.posicao)
            .all()
        )

        out: Dict[int, List[ReceitaModel]] = {}
        for vit_id, receita in rows:
            out.setdefault(vit_id, []).append(receita)
        return out

    # ----------------- Combos por (empresa, categoria) -----------------
    def listar_combos_por_vitrine_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> Dict[int, List[ComboModel]]:
        """
        Mesmo formato do método acima, mas restringe as vitrines à categoria informada.
        """
        rows: List[Tuple[int, ComboModel]] = (
            self.db.query(VitrineComboLink.vitrine_id, ComboModel)
            .join(
                VitrinesModel,
                VitrinesModel.id == VitrineComboLink.vitrine_id,
            )
            .join(
                ComboModel,
                ComboModel.id == VitrineComboLink.combo_id,
            )
            .join(
                VitrineCategoriaLink,
                VitrineCategoriaLink.vitrine_id == VitrineComboLink.vitrine_id,
            )
            .filter(
                VitrinesModel.empresa_id == empresa_id,
                ComboModel.empresa_id == empresa_id,
                ComboModel.ativo.is_(True),
                VitrineCategoriaLink.categoria_id == categoria_id,
            )
            .options(joinedload(ComboModel.itens))
            .order_by(VitrineComboLink.posicao)
            .all()
        )

        out: Dict[int, List[ComboModel]] = {}
        for vit_id, combo in rows:
            out.setdefault(vit_id, []).append(combo)
        return out

    # ----------------- Receitas por (empresa, categoria) -----------------
    def listar_receitas_por_vitrine_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> Dict[int, List]:
        """
        Mesmo formato do método acima, mas restringe as vitrines à categoria informada.
        """
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        rows: List[Tuple[int, ReceitaModel]] = (
            self.db.query(VitrineReceitaLink.vitrine_id, ReceitaModel)
            .join(
                VitrinesModel,
                VitrinesModel.id == VitrineReceitaLink.vitrine_id,
            )
            .join(
                ReceitaModel,
                ReceitaModel.id == VitrineReceitaLink.receita_id,
            )
            .join(
                VitrineCategoriaLink,
                VitrineCategoriaLink.vitrine_id == VitrineReceitaLink.vitrine_id,
            )
            .filter(
                VitrinesModel.empresa_id == empresa_id,
                ReceitaModel.empresa_id == empresa_id,
                ReceitaModel.disponivel.is_(True),
                ReceitaModel.ativo.is_(True),
                VitrineCategoriaLink.categoria_id == categoria_id,
            )
            .order_by(VitrineReceitaLink.posicao)
            .all()
        )

        out: Dict[int, List[ReceitaModel]] = {}
        for vit_id, receita in rows:
            out.setdefault(vit_id, []).append(receita)
        return out

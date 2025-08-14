# app/api/delivery/repositories/repo_produtos_dv.py
from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session, joinedload

from app.api.mensura.models.cadprod_model import ProdutoModel
from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel


class ProdutoDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- helper: unaccent disponível? ----
    _unaccent_checked: bool = False
    _has_unaccent_cache: bool = False

    _unaccent_checked: bool = False
    _has_unaccent_cache: bool = False

    def _has_unaccent(self) -> bool:
        if self._unaccent_checked:
            return self._has_unaccent_cache
        try:
            self.db.execute(text("SELECT unaccent(:s)"), {"s": "teste"})
            self._has_unaccent_cache = True
        except Exception:
            self._has_unaccent_cache = False
        self._unaccent_checked = True
        return self._has_unaccent_cache

    def search_produtos_da_empresa(
        self,
        *,
        empresa_id: int,
        q: Optional[str],
        offset: int,
        limit: int,
        apenas_disponiveis: bool = False,
        apenas_delivery: bool = True,
    ) -> List[ProdutoModel]:
        qry = (
            self.db.query(ProdutoModel)
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
            .options(
                joinedload(ProdutoModel.categoria),
                joinedload(ProdutoModel.produtos_empresa),
            )
            .order_by(ProdutoModel.descricao.asc())
        )

        if apenas_disponiveis:
            qry = qry.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True))

        if apenas_delivery:
            qry = qry.filter(ProdutoEmpModel.exibir_delivery.is_(True))

        if q and q.strip():
            term = f"%{q.strip()}%"
            if self._has_unaccent():
                qry = qry.filter(
                    or_(
                        func.unaccent(ProdutoModel.descricao).ilike(func.unaccent(term)),
                        ProdutoModel.cod_barras.ilike(term),
                    )
                )
            else:
                qry = qry.filter(
                    or_(
                        ProdutoModel.descricao.ilike(term),
                        ProdutoModel.cod_barras.ilike(term),
                    )
                )

        return qry.offset(offset).limit(limit).all()

    def count_search_total(
        self,
        *,
        empresa_id: int,
        q: Optional[str],
        apenas_disponiveis: bool = False,
        apenas_delivery: bool = True,
    ) -> int:
        qry = (
            self.db.query(func.count(ProdutoModel.cod_barras))
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
        )

        if apenas_disponiveis:
            qry = qry.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True))

        if apenas_delivery:
            qry = qry.filter(ProdutoEmpModel.exibir_delivery.is_(True))

        if q and q.strip():
            term = f"%{q.strip()}%"
            if self._has_unaccent():
                qry = qry.filter(
                    or_(
                        func.unaccent(ProdutoModel.descricao).ilike(func.unaccent(term)),
                        ProdutoModel.cod_barras.ilike(term),
                    )
                )
            else:
                qry = qry.filter(
                    or_(
                        ProdutoModel.descricao.ilike(term),
                        ProdutoModel.cod_barras.ilike(term),
                    )
                )

        return int(qry.scalar() or 0)



    def upsert_produto_emp(
        self,
        *,
        empresa_id: int,
        cod_barras: str,
        preco_venda: Decimal,
        custo: Optional[Decimal] = None,
        vitrine_id: Optional[int] = None,   # 👈 compat: cria vínculo N:N se vier preenchido
        sku_empresa: Optional[str] = None,
        disponivel: Optional[bool] = None,
        exibir_delivery: Optional[bool] = None,
    ) -> ProdutoEmpModel:
        pe = self.get_produto_emp(empresa_id, cod_barras)
        if pe:
            pe.preco_venda = preco_venda
            pe.custo = custo
            if sku_empresa is not None:
                pe.sku_empresa = sku_empresa
            if disponivel is not None:
                pe.disponivel = disponivel
            if exibir_delivery is not None:
                pe.exibir_delivery = exibir_delivery
        else:
            pe = ProdutoEmpModel(
                empresa_id=empresa_id,
                cod_barras=cod_barras,
                preco_venda=preco_venda,
                custo=custo,
                sku_empresa=sku_empresa,
                disponivel=True if disponivel is None else disponivel,
                exibir_delivery=True if exibir_delivery is None else exibir_delivery,
            )
            self.db.add(pe)

        self.db.flush()

        # 👇 compat: se vier vitrine_id, garante o vínculo N:N
        if vitrine_id is not None:
            vit = self.db.query(VitrinesModel).filter_by(id=vitrine_id).first()
            if vit and vit not in pe.vitrines:
                pe.vitrines.append(vit)
                self.db.flush()

        return pe
    # -------- CRUD Produto base --------
    def buscar_por_cod_barras(self, cod_barras: str) -> Optional[ProdutoModel]:
        return self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()

    def criar_produto(self, **data) -> ProdutoModel:
        obj = ProdutoModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def atualizar_produto(self, prod: ProdutoModel, **data) -> ProdutoModel:
        for f, v in data.items():
            setattr(prod, f, v)
        self.db.flush()
        return prod

    def deletar_produto(self, cod_barras: str) -> bool:
        prod = self.buscar_por_cod_barras(cod_barras)
        if not prod:
            return False
        self.db.delete(prod)
        self.db.flush()  # sem commit aqui
        return True

    def deletar_vinculo_produto_emp(self, empresa_id: int, cod_barras: str) -> bool:
        pe = self.get_produto_emp(empresa_id, cod_barras)
        if not pe:
            return False
        self.db.delete(pe)
        self.db.flush()
        return True

    def count_vinculos(self, cod_barras: str) -> int:
        return int(
            self.db.query(func.count(ProdutoEmpModel.empresa_id))
            .filter(ProdutoEmpModel.cod_barras == cod_barras)
            .scalar() or 0
        )

    # -------- Produto x Empresa --------
    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )

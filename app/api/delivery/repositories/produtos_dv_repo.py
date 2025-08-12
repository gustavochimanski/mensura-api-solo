# app/api/delivery/repositories/produtos_dv_repo.py
from __future__ import annotations
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel

class ProdutoDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    # -------- Listagem paginada --------
    def buscar_produtos_da_empresa(
        self, empresa_id: int, offset: int, limit: int,
        apenas_disponiveis: bool = False,
        apenas_delivery: bool = True
    ) -> List[ProdutoDeliveryModel]:
        q = (
            self.db.query(ProdutoDeliveryModel)
            .join(ProdutoEmpDeliveryModel, ProdutoDeliveryModel.cod_barras == ProdutoEmpDeliveryModel.cod_barras)
            .filter(ProdutoEmpDeliveryModel.empresa_id == empresa_id)
            .options(
                joinedload(ProdutoDeliveryModel.categoria),
                joinedload(ProdutoDeliveryModel.produtos_empresa),
            )
            .order_by(ProdutoDeliveryModel.created_at.desc())
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoDeliveryModel.ativo.is_(True), ProdutoEmpDeliveryModel.disponivel.is_(True))
        if apenas_delivery:
            q = q.filter(ProdutoEmpDeliveryModel.exibir_delivery.is_(True))
        return q.offset(offset).limit(limit).all()

    def contar_total(self, empresa_id: int, apenas_disponiveis: bool = False, apenas_delivery: bool = True) -> int:
        q = (
            self.db.query(func.count(ProdutoDeliveryModel.cod_barras))
            .join(ProdutoEmpDeliveryModel, ProdutoDeliveryModel.cod_barras == ProdutoEmpDeliveryModel.cod_barras)
            .filter(ProdutoEmpDeliveryModel.empresa_id == empresa_id)
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoDeliveryModel.ativo.is_(True), ProdutoEmpDeliveryModel.disponivel.is_(True))
        if apenas_delivery:
            q = q.filter(ProdutoEmpDeliveryModel.exibir_delivery.is_(True))
        return int(q.scalar() or 0)

    def upsert_produto_emp(
        self,
        *,
        empresa_id: int,
        cod_barras: str,
        preco_venda: Decimal,
        custo: Optional[Decimal] = None,
        vitrine_id: Optional[int] = None,
        sku_empresa: Optional[str] = None,
        disponivel: Optional[bool] = None,
        exibir_delivery: Optional[bool] = None,
    ) -> ProdutoEmpDeliveryModel:
        pe = self.get_produto_emp(empresa_id, cod_barras)
        if pe:
            pe.preco_venda = preco_venda
            pe.custo = custo
            pe.vitrine_id = vitrine_id
            if sku_empresa is not None:
                pe.sku_empresa = sku_empresa
            if disponivel is not None:
                pe.disponivel = disponivel
            if exibir_delivery is not None:
                pe.exibir_delivery = exibir_delivery
        else:
            pe = ProdutoEmpDeliveryModel(
                empresa_id=empresa_id,
                cod_barras=cod_barras,
                preco_venda=preco_venda,
                custo=custo,
                vitrine_id=vitrine_id,
                sku_empresa=sku_empresa,
                disponivel=True if disponivel is None else disponivel,
                exibir_delivery=True if exibir_delivery is None else exibir_delivery,
            )
            self.db.add(pe)
        self.db.flush()
        return pe

    # -------- CRUD Produto base --------
    def buscar_por_cod_barras(self, cod_barras: str) -> Optional[ProdutoDeliveryModel]:
        return self.db.query(ProdutoDeliveryModel).filter_by(cod_barras=cod_barras).first()

    def criar_produto(self, **data) -> ProdutoDeliveryModel:
        obj = ProdutoDeliveryModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def atualizar_produto(self, prod: ProdutoDeliveryModel, **data) -> ProdutoDeliveryModel:
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
            self.db.query(func.count(ProdutoEmpDeliveryModel.empresa_id))
            .filter(ProdutoEmpDeliveryModel.cod_barras == cod_barras)
            .scalar() or 0
        )

    # -------- Produto x Empresa --------
    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpDeliveryModel]:
        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )

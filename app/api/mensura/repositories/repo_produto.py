from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.delivery.models.vitrine_dv_model import VitrinesModel
from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.mensura.models.cadprod_model import ProdutoModel


# -------- Listagem paginada --------
class ProdutoMensuraRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_cod_barras(self, cod_barras: str) -> Optional[ProdutoModel]:
        return self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()

    def criar_produto(self, **data) -> ProdutoModel:
        obj = ProdutoModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def buscar_produtos_da_empresa(
            self, empresa_id: int, offset: int, limit: int,
            apenas_disponiveis: bool = False,
            apenas_delivery: bool = True
    ) -> List[ProdutoModel]:
        q = (
            self.db.query(ProdutoModel)
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
            .options(
                joinedload(ProdutoModel.categoria),
                joinedload(ProdutoModel.produtos_empresa),
            )
            .order_by(ProdutoModel.created_at.desc())
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True))
        if apenas_delivery:
            q = q.filter(ProdutoEmpModel.exibir_delivery.is_(True))
        return q.offset(offset).limit(limit).all()

    def contar_total(self, empresa_id: int, apenas_disponiveis: bool = False, apenas_delivery: bool = True) -> int:
        q = (
            self.db.query(func.count(ProdutoModel.cod_barras))
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True))
        if apenas_delivery:
            q = q.filter(ProdutoEmpModel.exibir_delivery.is_(True))
        return int(q.scalar() or 0)

    # -------- Produto x Empresa --------
    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )

    def upsert_produto_emp(
        self,
        *,
        empresa_id: int,
        cod_barras: str,
        preco_venda: Decimal,
        custo: Optional[Decimal] = None,
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
        return pe

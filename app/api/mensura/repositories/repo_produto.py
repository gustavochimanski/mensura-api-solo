from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.mensura.models.cadprod_model import ProdutoModel


# -------- Listagem paginada --------
class ProdutoMensuraRepository:
    def __init__(self, db: Session):
        self.db = db
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
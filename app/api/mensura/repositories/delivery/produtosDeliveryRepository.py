# repositories/produto_repository.py
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.mensura.models.cad_prod_delivery_model import ProdutoDeliveryModel
from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel


class ProdutoDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_produtos_da_empresa(self, cod_empresa: int, offset: int, limit: int):
        return (
            self.db.query(ProdutoDeliveryModel)
            .join(ProdutosEmpDeliveryModel, ProdutoDeliveryModel.cod_barras == ProdutosEmpDeliveryModel.cod_barras)
            .filter(ProdutosEmpDeliveryModel.empresa == cod_empresa)
            .options(
                joinedload(ProdutoDeliveryModel.categoria),
                joinedload(ProdutoDeliveryModel.produtos_empresa),
            )
            .order_by(ProdutoDeliveryModel.data_cadastro.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def contar_total(self, cod_empresa: int):
        return (
            self.db.query(func.count(ProdutoDeliveryModel.id))
            .join(ProdutosEmpDeliveryModel, ProdutoDeliveryModel.cod_barras == ProdutosEmpDeliveryModel.cod_barras)
            .filter(ProdutosEmpDeliveryModel.empresa == cod_empresa)
            .scalar()
        )

    def buscar_por_cod_barras(self, cod_barras: str):
        return (
            self.db.query(ProdutoDeliveryModel)
            .filter(ProdutoDeliveryModel.cod_barras == cod_barras)
            .first()
        )

    def criar_novo_produto(self, produto: ProdutoDeliveryModel):
        self.db.add(produto)
        self.db.commit()
        self.db.refresh(produto)
        return produto

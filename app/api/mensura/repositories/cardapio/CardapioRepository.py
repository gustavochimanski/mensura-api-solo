# app/repositories/cardapio_repository.py
from typing import List
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.api.mensura.models.cad_categoria_delivery_model import CategoriaDeliveryModel
from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel
from app.api.mensura.models.sub_categoria_model import SubCategoriaModel


class CardapioRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_produtos_emp(self, cod_empresa: int) -> List[ProdutosEmpDeliveryModel]:
        return (
            self.db.query(ProdutosEmpDeliveryModel)
            .options(joinedload(ProdutosEmpDeliveryModel.produto))
            .filter(ProdutosEmpDeliveryModel.empresa == cod_empresa)
            .all()
        )

    def listar_categorias(self, empresa_id: int) -> List[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .filter(CategoriaDeliveryModel.empresa_id == empresa_id)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )

    def listar_vitrines(self, empresa_id: int) -> List[SubCategoriaModel]:
        return (
            self.db.query(SubCategoriaModel)
            .filter(SubCategoriaModel.cod_empresa == empresa_id)
            .order_by(SubCategoriaModel.ordem)
            .all()
        )

    def listar_produtos_emp_por_categoria_e_sub(
            self, cod_empresa: int, cod_categoria: int
    ) -> List[ProdutosEmpDeliveryModel]:
        return (
            self.db.query(ProdutosEmpDeliveryModel)
            .join(ProdutosEmpDeliveryModel.produto)
            .options(joinedload(ProdutosEmpDeliveryModel.produto))
            .filter(ProdutosEmpDeliveryModel.empresa == cod_empresa)
            .filter(ProdutosEmpDeliveryModel.produto.has(cod_categoria=cod_categoria))
            .all()
        )


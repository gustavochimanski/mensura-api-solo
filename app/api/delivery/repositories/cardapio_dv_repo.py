# app/repositories/cardapio_repository.py
from typing import List, Dict
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.api.delivery.models.categoria_dv_model import CategoriaDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.vitrine_dv_model import VitrinesModel


class CardapioRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_produtos_emp(self, cod_empresa: int) -> List[ProdutoEmpDeliveryModel]:
        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(ProdutoEmpDeliveryModel.empresa == cod_empresa)
            .all()
        )

    def listar_categorias(self) -> List[CategoriaDeliveryModel]:
        return (
            self.db.query(CategoriaDeliveryModel)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )

    def listar_vitrines(self, empresa_id: int) -> List[VitrinesModel]:
        """
        Retorna vitrines que possuem produtos da empresa.
        """
        return (
            self.db.query(VitrinesModel)
            .join(ProdutoEmpDeliveryModel, ProdutoEmpDeliveryModel.vitrine_id == VitrinesModel.id)
            .filter(ProdutoEmpDeliveryModel.empresa == empresa_id)
            .distinct()
            .order_by(VitrinesModel.ordem)
            .all()
        )

    def listar_produtos_emp_por_categoria_e_sub(self, cod_empresa: int, cod_categoria: int) -> List[ProdutoEmpDeliveryModel]:
        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .join(ProdutoEmpDeliveryModel.produto)
            .options(joinedload(ProdutoEmpDeliveryModel.produto))
            .filter(
                ProdutoEmpDeliveryModel.empresa == cod_empresa,
                ProdutoEmpDeliveryModel.produto.has(cod_categoria=cod_categoria)
            )
            .all()
        )

    def listar_vitrines_com_produtos_empresa_categoria(
            self, empresa_id: int, cod_categoria: int
    ) -> Dict[int, List[ProdutoEmpDeliveryModel]]:
        """
        Retorna um dicionário onde a chave é o ID da vitrine e o valor é a lista de produtos daquela empresa e categoria.
        """
        produtos = self.listar_produtos_emp_por_categoria_e_sub(empresa_id, cod_categoria)

        agrupado: Dict[int, List[ProdutoEmpDeliveryModel]] = defaultdict(list)
        for p in produtos:
            if p.vitrine_id is not None:
                agrupado[p.vitrine_id].append(p)

        return agrupado



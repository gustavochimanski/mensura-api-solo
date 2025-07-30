# repositories/produto_repository.py
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutosEmpDeliveryModel


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
            self.db.query(func.count(ProdutoDeliveryModel.cod_barras))
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


    def update_produto(self, cod_barras: str, update_data: dict) -> ProdutoDeliveryModel:
        """
        Atualiza o produto e seus dados na tabela de relação com empresa.
        update_data deve conter as chaves:
         - descricao, cod_categoria, imagem, data_cadastro
         - preco_venda, custo, vitrine_id
        """
        prod = self.db.query(ProdutoDeliveryModel).filter_by(cod_barras=cod_barras).first()
        if not prod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

        # Atualiza campos do próprio produto
        for attr in ("descricao","cod_categoria","imagem","data_cadastro"):
            if attr in update_data and update_data[attr] is not None:
                setattr(prod, attr, update_data[attr])

        # Atualiza preço, custo e vitrine na relação ProdutosEmpDeliveryModel
        for pe in prod.produtos_empresa:
            if "preco_venda" in update_data:
                pe.preco_venda = update_data["preco_venda"]
            if "custo" in update_data:
                pe.custo = update_data["custo"]
            if "vitrine_id" in update_data:
                pe.vitrine_id = update_data["vitrine_id"]

        try:
            self.db.commit()
            self.db.refresh(prod)
            return prod
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar produto"
            )

    def delete_produto(self, cod_barras: str) -> bool:
        """
        Tenta deletar o produto; retorna True se encontrado e deletado,
        False se não havia produto com esse cod_barras.
        """
        prod = self.db.query(ProdutoDeliveryModel).filter_by(cod_barras=cod_barras).first()
        if not prod:
            return False

        self.db.delete(prod)
        self.db.commit()
        return True
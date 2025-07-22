from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel
from app.api.mensura.models.sub_categoria_model import SubCategoriaModel
from app.api.mensura.schemas.delivery.categorias.sub_categoria_schema import CriarSubCategoriaRequest


class SubCategoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, cod_empresa: int, cod_categoria: int | None = None):
        """
        Retorna as subcategorias da empresa, podendo filtrar por categoria.
        """
        query = self.db.query(SubCategoriaModel).filter(
            SubCategoriaModel.cod_empresa == cod_empresa
        )

        if cod_categoria is not None:
            query = query.filter(SubCategoriaModel.cod_categoria == cod_categoria)

        return query.order_by(SubCategoriaModel.ordem).all()

    def create(self, dados: CriarSubCategoriaRequest):
        """
        Cria uma nova subcategoria/vitrine.
        Gera slug automático se não fornecido.
        """
        slug_value = dados.titulo.lower().replace(" ", "-")
        nova = SubCategoriaModel(
            cod_empresa=dados.cod_empresa,
            cod_categoria=dados.cod_categoria,
            titulo=dados.titulo,
            slug=slug_value,
            ordem=dados.ordem
        )
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar subcategoria"
            )
        return nova

    def delete(self, sub_id: int):
        """
        Deleta a subcategoria pelo ID, se não houver produtos relacionados.
        Lança 404 se não encontrar, e 400 se houver produtos vinculados.
        """
        sub = self.db.query(SubCategoriaModel).filter_by(id=sub_id).first()
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subcategoria não encontrada"
            )

        # 🔎 Verificar se existem produtos vinculados via ORM
        produto_vinculado = (
            self.db.query(ProdutosEmpDeliveryModel)
            .filter(ProdutosEmpDeliveryModel.subcategoria_id == sub_id)
            .first()
        )

        if produto_vinculado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir. Existem produtos vinculados a esta subcategoria."
            )

        self.db.delete(sub)
        self.db.commit()


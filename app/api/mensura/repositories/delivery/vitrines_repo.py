from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from slugify import slugify

from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel
from app.api.mensura.models.vitrines_model import VitrinesModel
from app.api.mensura.schemas.delivery.vitrine_schema import CriarVitrineRequest


class VitrineRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, cod_empresa: int, cod_categoria: int | None = None):
        """
        Retorna todas as vitrines da categoria (se informada),
        mesmo que não tenham produtos vinculados à empresa.
        Marca apenas se têm produtos da empresa.
        """
        # Subquery com produtos da empresa
        subquery = (
            self.db.query(ProdutosEmpDeliveryModel.vitrine_id)
            .filter(ProdutosEmpDeliveryModel.empresa == cod_empresa)
            .distinct()
            .subquery()
        )

        query = self.db.query(VitrinesModel).outerjoin(
            subquery, VitrinesModel.id == subquery.c.vitrine_id
        )

        if cod_categoria is not None:
            query = query.filter(VitrinesModel.cod_categoria == cod_categoria)

        return query.order_by(VitrinesModel.ordem).all()

    def create(self, dados: CriarVitrineRequest):
        """
        Cria uma nova vitrine.
        """
        slug_value = slugify(dados.titulo)
        nova = VitrinesModel(
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
                detail="Erro ao criar Vitrine"
            )
        return nova

    def delete(self, sub_id: int):
        """
        Deleta a Vitrine se não houver produtos vinculados.
        """
        sub = self.db.query(VitrinesModel).filter_by(id=sub_id).first()
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vitrine não encontrada"
            )

        produto_vinculado = (
            self.db.query(ProdutosEmpDeliveryModel)
            .filter(ProdutosEmpDeliveryModel.vitrine_id == sub_id)
            .first()
        )

        if produto_vinculado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir. Existem produtos vinculados a esta Vitrine."
            )

        self.db.delete(sub)
        self.db.commit()

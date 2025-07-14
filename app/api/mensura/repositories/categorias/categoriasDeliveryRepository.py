from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.mensura.models.cad_categoria_delivery_model import CategoriaDeliveryModel
from app.api.mensura.schemas.delivery.categorias.categoria_schema import CategoriaDeliveryIn

class CategoriaDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> list[CategoriaDeliveryModel]:
        """
        Retorna todas as categorias, ordenadas por posição (posicao asc).
        """
        return (
            self.db
            .query(CategoriaDeliveryModel)
            .order_by(CategoriaDeliveryModel.posicao)
            .all()
        )

    def create(self, dados: CategoriaDeliveryIn) -> CategoriaDeliveryModel:
        """
        Cria uma nova categoria de delivery.
        Se `dados.slug` estiver vazio, gera a partir de `descricao`.
        Usa o campo `posicao` caso seja informado.
        """
        # Gera slug automático se não vier
        slug_value = dados.slug or dados.descricao.lower().replace(" ", "-")

        nova = CategoriaDeliveryModel(
            descricao=dados.descricao,
            slug=slug_value,
            slug_pai=dados.slug_pai,
            imagem=dados.imagem,
            posicao=dados.posicao
        )
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar categoria"
            )
        return nova



    def delete(self, id: int) -> None:
        """
        Deleta a categoria pelo ID.
        Lança 404 se não encontrar.
        """
        cat = self.db.query(CategoriaDeliveryModel).filter_by(id=id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada"
            )
        self.db.delete(cat)
        self.db.commit()



    def update(self, cat_id: int, update_data: dict) -> CategoriaDeliveryModel:
        """
        Atualiza os campos da categoria com base no ID.
        Apenas campos presentes em `update_data` são atualizados.
        """
        cat = self.db.query(CategoriaDeliveryModel).filter_by(id=cat_id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada"
            )

        # Atualiza apenas os campos fornecidos
        for key, value in update_data.items():
            if value is not None:  # Ignora campos nulos (como imagem se não for enviada)
                setattr(cat, key, value)

        try:
            self.db.commit()
            self.db.refresh(cat)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar categoria"
            )

        return cat


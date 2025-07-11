from sqlalchemy.orm import Session
from app.api.public.models.produtos.cadprod import ProdutoModel
from app.api.public.schemas.cadProdPublicDTO_type import CadProdPublicDTO
from sqlalchemy import func

from sqlalchemy import func, desc  # já importa desc por garantia

class CadProdPublicRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_paginated(self, page: int = 1, limit: int = 30) -> dict:
        offset = (page - 1) * limit

        # Consulta paginada com ordenação por data de cadastro (do mais recente para o mais antigo)
        query = (
            self.db.query(ProdutoModel)
            .order_by(ProdutoModel.cadp_dtcadastro.desc())
            .offset(offset)
            .limit(limit)
        )

        produtos = query.all()

        # Total de registros
        total = self.db.query(func.count(ProdutoModel.cadp_codigo)).scalar()

        return {
            "data": [CadProdPublicDTO.model_validate(p, from_attributes=True) for p in produtos],
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": offset + limit < total
        }

    def put_by_filed(self, produto_id: int, field: str, value:any ):
        produto =  self.db.query(ProdutoModel).filter(ProdutoModel.cadp_codigo == produto_id).first()
        if produto is None:
            from sqlalchemy.exc import NoResultFound
            raise NoResultFound("Produto Não Encontrado")

        campos_protegidos = ["cadp_codigo", "cadp_dtcadastro"]

        if field in campos_protegidos:
            raise ValueError(f"O campo '{field}' não pode ser modificado.")

        if not hasattr(produto, field):
            raise ValueError(f"Campo '{field}' inválido")

        setattr(produto, field, value)
        self.db.commit()
        self.db.refresh(produto)
        return {"message": "Campo Atualizado com sucesso"}


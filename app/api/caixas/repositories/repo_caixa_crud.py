from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.api.caixas.models.model_caixa import CaixaModel
from app.utils.logger import logger


class CaixaCRUDRepository:
    """Repository para CRUD de caixas cadastrados"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, caixa_id: int) -> Optional[CaixaModel]:
        """Busca um caixa por ID com relacionamentos"""
        return (
            self.db.query(CaixaModel)
            .options(
                joinedload(CaixaModel.empresa)
            )
            .filter(CaixaModel.id == caixa_id)
            .first()
        )

    def list(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CaixaModel]:
        """Lista caixas com filtros opcionais"""
        query = (
            self.db.query(CaixaModel)
            .options(
                joinedload(CaixaModel.empresa)
            )
        )

        if empresa_id:
            query = query.filter(CaixaModel.empresa_id == empresa_id)
        
        if ativo is not None:
            query = query.filter(CaixaModel.ativo == ativo)

        query = query.order_by(CaixaModel.nome.asc())
        query = query.offset(skip)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def create(self, **data) -> CaixaModel:
        """Cria um novo caixa"""
        caixa = CaixaModel(**data)
        self.db.add(caixa)
        self.db.commit()
        self.db.refresh(caixa)
        logger.info(f"[Caixa] Criado caixa_id={caixa.id} empresa_id={caixa.empresa_id} nome={caixa.nome}")
        return caixa

    def update(self, caixa: CaixaModel, **data) -> CaixaModel:
        """Atualiza um caixa existente"""
        for key, value in data.items():
            if hasattr(caixa, key) and value is not None:
                setattr(caixa, key, value)
        self.db.commit()
        self.db.refresh(caixa)
        return caixa

    def delete(self, caixa: CaixaModel) -> None:
        """Remove um caixa (soft delete - marca como inativo)"""
        caixa.ativo = False
        self.db.commit()
        logger.info(f"[Caixa] Desativado caixa_id={caixa.id}")


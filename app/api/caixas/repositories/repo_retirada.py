from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.api.caixas.models.model_retirada import RetiradaModel


class RetiradaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        empresa_id: int,
        caixa_abertura_id: int,
        usuario_id: int,
        tipo: str,
        valor: float,
        observacoes: Optional[str] = None
    ) -> RetiradaModel:
        """Cria uma nova retirada"""
        retirada = RetiradaModel(
            empresa_id=empresa_id,
            caixa_abertura_id=caixa_abertura_id,
            usuario_id=usuario_id,
            tipo=tipo,
            valor=valor,
            observacoes=observacoes
        )
        self.db.add(retirada)
        self.db.flush()
        return retirada

    def get_by_id(self, retirada_id: int, empresa_id: Optional[int] = None) -> Optional[RetiradaModel]:
        """Busca uma retirada por ID, opcionalmente filtrada por empresa"""
        query = (
            self.db.query(RetiradaModel)
            .options(joinedload(RetiradaModel.usuario))
            .filter(RetiradaModel.id == retirada_id)
        )
        
        if empresa_id:
            query = query.filter(RetiradaModel.empresa_id == empresa_id)
        
        return query.first()

    def list_by_caixa_abertura(
        self,
        empresa_id: int,
        caixa_abertura_id: int,
        tipo: Optional[str] = None
    ) -> List[RetiradaModel]:
        """Lista retiradas de uma abertura de caixa, opcionalmente filtradas por tipo"""
        query = (
            self.db.query(RetiradaModel)
            .options(joinedload(RetiradaModel.usuario))
            .filter(
                and_(
                    RetiradaModel.empresa_id == empresa_id,
                    RetiradaModel.caixa_abertura_id == caixa_abertura_id
                )
            )
        )
        
        if tipo:
            query = query.filter(RetiradaModel.tipo == tipo)
        
        return query.order_by(RetiradaModel.created_at.desc()).all()

    def delete(self, retirada: RetiradaModel):
        """Exclui uma retirada"""
        self.db.delete(retirada)
        self.db.flush()

    def get_total_retiradas(self, empresa_id: int, caixa_abertura_id: int) -> float:
        """Retorna o total de retiradas de uma abertura de caixa"""
        from sqlalchemy import func
        result = (
            self.db.query(func.sum(RetiradaModel.valor))
            .filter(
                and_(
                    RetiradaModel.empresa_id == empresa_id,
                    RetiradaModel.caixa_abertura_id == caixa_abertura_id
                )
            )
            .scalar()
        )
        return float(result or 0)


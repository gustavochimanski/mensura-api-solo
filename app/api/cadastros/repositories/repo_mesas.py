from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.api.cadastros.models.model_mesa import MesaModel, StatusMesa


class MesaRepository:
    """Repository para operações com mesas."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, mesa_id: int) -> Optional[MesaModel]:
        """Busca uma mesa por ID."""
        return self.db.query(MesaModel).filter_by(id=mesa_id).first()

    def get_by_codigo(self, codigo: Decimal, empresa_id: int) -> Optional[MesaModel]:
        """Busca uma mesa por código e empresa."""
        return (
            self.db.query(MesaModel)
            .filter(
                and_(
                    MesaModel.codigo == codigo,
                    MesaModel.empresa_id == empresa_id,
                )
            )
            .first()
        )

    def get_by_numero(self, numero: str, empresa_id: int) -> Optional[MesaModel]:
        """Busca uma mesa por número e empresa."""
        return (
            self.db.query(MesaModel)
            .filter(
                and_(
                    MesaModel.numero == numero,
                    MesaModel.empresa_id == empresa_id,
                )
            )
            .first()
        )

    def ocupar_mesa(self, mesa_id: int, empresa_id: int) -> MesaModel:
        """Ocupa uma mesa (muda status para OCUPADA)."""
        mesa = self.get_by_id(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} não encontrada")
        if mesa.empresa_id != empresa_id:
            raise ValueError("Mesa não pertence à empresa informada")
        
        mesa.status = StatusMesa.OCUPADA
        self.db.commit()
        self.db.refresh(mesa)
        return mesa

    def liberar_mesa(self, mesa_id: int, empresa_id: int) -> MesaModel:
        """Libera uma mesa (muda status para DISPONIVEL)."""
        mesa = self.get_by_id(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} não encontrada")
        if mesa.empresa_id != empresa_id:
            raise ValueError("Mesa não pertence à empresa informada")
        
        mesa.status = StatusMesa.DISPONIVEL
        mesa.cliente_atual_id = None
        self.db.commit()
        self.db.refresh(mesa)
        return mesa

    def listar_por_empresa(self, empresa_id: int, apenas_ativas: bool = True) -> list[MesaModel]:
        """Lista todas as mesas de uma empresa."""
        query = self.db.query(MesaModel).filter_by(empresa_id=empresa_id)
        if apenas_ativas:
            query = query.filter_by(ativa="S")
        return query.order_by(MesaModel.numero).all()


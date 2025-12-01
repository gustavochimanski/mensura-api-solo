from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

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

    def criar(self, mesa: MesaModel) -> MesaModel:
        """Cria uma nova mesa."""
        self.db.add(mesa)
        self.db.flush()
        return mesa

    def atualizar(self, mesa: MesaModel) -> MesaModel:
        """Atualiza uma mesa existente."""
        self.db.flush()
        self.db.refresh(mesa)
        return mesa

    def deletar(self, mesa_id: int, empresa_id: int) -> bool:
        """Deleta uma mesa."""
        mesa = self.get_by_id(mesa_id)
        if not mesa:
            return False
        if mesa.empresa_id != empresa_id:
            raise ValueError("Mesa não pertence à empresa informada")
        self.db.delete(mesa)
        return True

    def buscar(self, empresa_id: int, q: Optional[str] = None, status: Optional[str] = None, 
               ativa: Optional[str] = None, limit: int = 30, offset: int = 0) -> list[MesaModel]:
        """Busca mesas com filtros."""
        query = self.db.query(MesaModel).filter_by(empresa_id=empresa_id)
        
        if q:
            query = query.filter(
                or_(
                    MesaModel.numero.ilike(f"%{q}%"),
                    MesaModel.descricao.ilike(f"%{q}%")
                )
            )
        
        if status:
            query = query.filter_by(status=status)
        
        if ativa:
            query = query.filter_by(ativa=ativa)
        
        return query.order_by(MesaModel.numero).offset(offset).limit(limit).all()

    def reservar_mesa(self, mesa_id: int, empresa_id: int) -> MesaModel:
        """Reserva uma mesa (muda status para RESERVADA)."""
        mesa = self.get_by_id(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} não encontrada")
        if mesa.empresa_id != empresa_id:
            raise ValueError("Mesa não pertence à empresa informada")
        
        mesa.status = StatusMesa.RESERVADA
        self.db.commit()
        self.db.refresh(mesa)
        return mesa

    def atualizar_status(self, mesa_id: int, empresa_id: int, novo_status: str) -> MesaModel:
        """Atualiza o status de uma mesa."""
        mesa = self.get_by_id(mesa_id)
        if not mesa:
            raise ValueError(f"Mesa {mesa_id} não encontrada")
        if mesa.empresa_id != empresa_id:
            raise ValueError("Mesa não pertence à empresa informada")
        
        mesa.status = StatusMesa(novo_status)
        if novo_status == "D":
            mesa.cliente_atual_id = None
        self.db.commit()
        self.db.refresh(mesa)
        return mesa

    def obter_stats(self, empresa_id: int) -> dict:
        """Obtém estatísticas das mesas de uma empresa."""
        base_query = self.db.query(MesaModel).filter_by(empresa_id=empresa_id)
        
        total = base_query.count()
        disponiveis = base_query.filter(MesaModel.status == StatusMesa.DISPONIVEL).count()
        ocupadas = base_query.filter(MesaModel.status == StatusMesa.OCUPADA).count()
        reservadas = base_query.filter(MesaModel.status == StatusMesa.RESERVADA).count()
        inativas = base_query.filter(MesaModel.ativa == "N").count()
        
        return {
            "total": total,
            "disponiveis": disponiveis,
            "ocupadas": ocupadas,
            "reservadas": reservadas,
            "inativas": inativas
        }


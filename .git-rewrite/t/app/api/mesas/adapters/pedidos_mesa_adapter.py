from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.mesas.contracts.pedidos_mesa_contract import (
    IMesaPedidosContract,
    MesaPedidoDTO,
    ClienteMinDTO,
)
from app.api.mesas.repositories.repo_pedidos_mesa import PedidoMesaRepository
from app.api.mesas.models.model_pedido_mesa import PedidoMesaModel, StatusPedidoMesa


class MesaPedidosAdapter(IMesaPedidosContract):
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoMesaRepository(db)

    def _to_dto(self, p: PedidoMesaModel) -> MesaPedidoDTO:
        cliente_min = None
        if getattr(p, "cliente", None):
            cliente_min = ClienteMinDTO(id=getattr(p.cliente, "id", None), nome=getattr(p.cliente, "nome", None))
        mesa_numero = None
        if getattr(p, "mesa", None):
            mesa_numero = str(getattr(p.mesa, "numero", None))
        status_value = p.status.value if hasattr(p.status, "value") else str(p.status)
        return MesaPedidoDTO(
            id=p.id,
            empresa_id=p.empresa_id,
            cliente=cliente_min,
            valor_total=getattr(p, "valor_total", 0) or 0,
            created_at=p.created_at,
            updated_at=getattr(p, "updated_at", None),
            status=status_value,
            observacoes=getattr(p, "observacoes", None),
            mesa_numero=mesa_numero,
        )

    def listar_abertos(self, *, empresa_id: int) -> List[MesaPedidoDTO]:
        pedidos = self.repo.list_abertos_all(empresa_id=empresa_id)
        return [self._to_dto(p) for p in pedidos]

    def listar_finalizados(self, *, empresa_id: int, date_filter: date) -> List[MesaPedidoDTO]:
        """Lista pedidos finalizados (status ENTREGUE)"""
        from datetime import datetime
        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_, and_
        
        # date_filter é sempre obrigatório
        start_dt = datetime.combine(date_filter, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)
        
        query = (
            self.db.query(PedidoMesaModel)
            .options(
                joinedload(PedidoMesaModel.cliente),
                joinedload(PedidoMesaModel.mesa),
            )
            .filter(
                PedidoMesaModel.empresa_id == empresa_id,
                PedidoMesaModel.status == StatusPedidoMesa.ENTREGUE.value,
            )
        )
        
        # Busca pedidos criados naquele dia OU pedidos entregues naquele dia
        # (mesmo que tenham sido criados em outro dia)
        query = query.filter(
            or_(
                # Pedidos criados naquele dia
                and_(
                    PedidoMesaModel.created_at >= start_dt,
                    PedidoMesaModel.created_at < end_dt
                ),
                # Pedidos entregues naquele dia (baseado em updated_at quando status = E)
                and_(
                    PedidoMesaModel.updated_at >= start_dt,
                    PedidoMesaModel.updated_at < end_dt
                )
            )
        )
        
        pedidos = query.order_by(PedidoMesaModel.created_at.desc()).all()
        return [self._to_dto(p) for p in pedidos]

    def listar_pendentes_impressao(self, *, empresa_id: int) -> List[MesaPedidoDTO]:
        query = (
            self.db.query(PedidoMesaModel)
            .filter(PedidoMesaModel.empresa_id == empresa_id)
            .filter(PedidoMesaModel.status == StatusPedidoMesa.IMPRESSAO.value)
            .order_by(PedidoMesaModel.created_at.desc())
        )
        pedidos = query.all()
        return [self._to_dto(p) for p in pedidos]



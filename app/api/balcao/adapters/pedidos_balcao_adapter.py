from __future__ import annotations

from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.balcao.contracts.pedidos_balcao_contract import (
    IBalcaoPedidosContract,
    BalcaoPedidoDTO,
    ClienteMinDTO,
)
from app.api.balcao.repositories.repo_pedidos_balcao import PedidoBalcaoRepository
from app.api.balcao.models.model_pedido_balcao import PedidoBalcaoModel, StatusPedidoBalcao


class BalcaoPedidosAdapter(IBalcaoPedidosContract):
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoBalcaoRepository(db)

    def _to_dto(self, p: PedidoBalcaoModel) -> BalcaoPedidoDTO:
        cliente_min = None
        if getattr(p, "cliente", None):
            cliente_min = ClienteMinDTO(id=getattr(p.cliente, "id", None), nome=getattr(p.cliente, "nome", None))
        mesa_num = getattr(p, "mesa", None)
        mesa_numero = str(mesa_num.numero) if mesa_num else None
        status_value = p.status.value if hasattr(p.status, "value") else str(p.status)
        return BalcaoPedidoDTO(
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

    def listar_abertos(self, *, empresa_id: int) -> List[BalcaoPedidoDTO]:
        pedidos = self.repo.list_abertos_all(empresa_id=empresa_id)
        return [self._to_dto(p) for p in pedidos]

    def listar_finalizados(self, *, empresa_id: int, date_filter: date) -> List[BalcaoPedidoDTO]:
        pedidos = self.repo.list_finalizados(data_filtro=date_filter, empresa_id=empresa_id)
        return [self._to_dto(p) for p in pedidos]

    def listar_pendentes_impressao(self, *, empresa_id: int) -> List[BalcaoPedidoDTO]:
        from sqlalchemy.orm import load_only
        # Carrega apenas os campos necessários, evitando campos novos que podem não existir no banco ainda
        query = (
            self.db.query(PedidoBalcaoModel)
            .options(
                load_only(
                    PedidoBalcaoModel.id,
                    PedidoBalcaoModel.empresa_id,
                    PedidoBalcaoModel.mesa_id,
                    PedidoBalcaoModel.cliente_id,
                    PedidoBalcaoModel.numero_pedido,
                    PedidoBalcaoModel.status,
                    PedidoBalcaoModel.observacoes,
                    PedidoBalcaoModel.produtos_snapshot,
                    PedidoBalcaoModel.valor_total,
                    PedidoBalcaoModel.created_at,
                    PedidoBalcaoModel.updated_at,
                )
            )
            .filter(PedidoBalcaoModel.empresa_id == empresa_id)
            .filter(PedidoBalcaoModel.status == StatusPedidoBalcao.IMPRESSAO.value)
            .order_by(PedidoBalcaoModel.created_at.desc())
        )
        pedidos = query.all()
        return [self._to_dto(p) for p in pedidos]



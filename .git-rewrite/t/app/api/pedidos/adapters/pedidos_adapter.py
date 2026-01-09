"""
Adapter (Implementação) do contract de pedidos.
"""
from __future__ import annotations

from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session

from app.api.pedidos.contracts.pedidos_contract import (
    IPedidosContract,
    PedidoMinDTO,
    ClienteMinDTO,
    TipoPedidoDTO,
    StatusPedidoDTO,
)
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido import PedidoModel, TipoPedido, StatusPedido
from app.api.pedidos.utils.helpers import enum_value


class PedidosAdapter(IPedidosContract):
    """Implementação do contrato de pedidos baseada nos repositórios."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)

    def _to_pedido_min_dto(self, pedido: PedidoModel) -> PedidoMinDTO:
        """Converte modelo de pedido para DTO mínimo."""
        # Cliente
        cliente_min = None
        if getattr(pedido, "cliente", None) and pedido.cliente:
            cliente_min = ClienteMinDTO(
                id=getattr(pedido.cliente, "id", None),
                nome=getattr(pedido.cliente, "nome", None)
            )
        
        # Status e tipo
        status_value = enum_value(pedido.status)
        tipo_value = enum_value(pedido.tipo_pedido)
        
        # Converte enum string para DTO enum
        try:
            status_dto = StatusPedidoDTO(status_value)
        except ValueError:
            status_dto = StatusPedidoDTO.PENDENTE  # Fallback
        
        try:
            tipo_dto = TipoPedidoDTO(tipo_value)
        except ValueError:
            tipo_dto = TipoPedidoDTO.BALCAO  # Fallback
        
        return PedidoMinDTO(
            id=pedido.id,
            empresa_id=pedido.empresa_id,
            numero_pedido=pedido.numero_pedido,
            tipo_pedido=tipo_dto,
            status=status_dto,
            valor_total=getattr(pedido, "valor_total", 0) or 0,
            cliente=cliente_min,
            mesa_id=getattr(pedido, "mesa_id", None),
            endereco_id=getattr(pedido, "endereco_id", None),
            created_at=pedido.created_at,
            updated_at=getattr(pedido, "updated_at", None),
            observacoes=getattr(pedido, "observacoes", None),
        )

    def obter_pedido_por_id(self, pedido_id: int) -> Optional[PedidoMinDTO]:
        """Obtém um pedido por ID."""
        try:
            pedido = self.repo.get(pedido_id)
            return self._to_pedido_min_dto(pedido)
        except Exception:
            return None

    def listar_abertos(
        self,
        *,
        empresa_id: int,
        tipo_pedido: Optional[TipoPedidoDTO] = None
    ) -> List[PedidoMinDTO]:
        """Lista pedidos abertos (não finalizados)."""
        tipo_str = enum_value(tipo_pedido)
        pedidos = self.repo.list_abertos(empresa_id=empresa_id, tipo_pedido=tipo_str)
        return [self._to_pedido_min_dto(p) for p in pedidos]

    def listar_finalizados(
        self,
        *,
        empresa_id: int,
        data_filtro: Optional[date] = None,
        tipo_pedido: Optional[TipoPedidoDTO] = None
    ) -> List[PedidoMinDTO]:
        """Lista pedidos finalizados (status ENTREGUE)."""
        if data_filtro is None:
            data_filtro = date.today()
        
        tipo_str = enum_value(tipo_pedido)
        pedidos = self.repo.list_finalizados(
            data_filtro,
            empresa_id=empresa_id,
            tipo_pedido=tipo_str
        )
        return [self._to_pedido_min_dto(p) for p in pedidos]

    def listar_por_cliente(
        self,
        cliente_id: int,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[TipoPedidoDTO] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[PedidoMinDTO]:
        """Lista pedidos de um cliente específico."""
        tipo_str = enum_value(tipo_pedido)
        pedidos = self.repo.list_by_cliente(
            cliente_id,
            empresa_id=empresa_id,
            tipo_pedido=tipo_str,
            skip=skip,
            limit=limit
        )
        return [self._to_pedido_min_dto(p) for p in pedidos]

    def listar_abertos_por_mesa(
        self,
        mesa_id: int,
        *,
        empresa_id: Optional[int] = None
    ) -> List[PedidoMinDTO]:
        """Lista pedidos abertos associados a uma mesa."""
        pedidos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=empresa_id)
        return [self._to_pedido_min_dto(p) for p in pedidos]

    def contar_pedidos_abertos(
        self,
        *,
        empresa_id: int,
        tipo_pedido: Optional[TipoPedidoDTO] = None
    ) -> int:
        """Conta quantos pedidos estão abertos."""
        tipo_str = enum_value(tipo_pedido)
        pedidos = self.repo.list_abertos(empresa_id=empresa_id, tipo_pedido=tipo_str)
        return len(pedidos)


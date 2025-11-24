from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.api.pedidos.schemas.schema_pedido import PedidoResponseSimplificado, TipoPedidoCheckoutEnum
from app.api.mesas.schemas.schema_pedido_mesa import PedidoMesaOut
from app.api.balcao.schemas.schema_pedido_balcao import PedidoBalcaoOut


class PedidoClienteListItem(BaseModel):
    """Item unificado para listagem de pedidos do cliente independente da origem."""

    tipo_pedido: TipoPedidoCheckoutEnum
    criado_em: datetime
    atualizado_em: Optional[datetime] = None
    status_codigo: str
    status_descricao: Optional[str] = None
    numero_pedido: Optional[str] = None
    valor_total: float

    delivery: Optional[PedidoResponseSimplificado] = None
    mesa: Optional[PedidoMesaOut] = None
    balcao: Optional[PedidoBalcaoOut] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _validate_payload(self) -> "PedidoClienteListItem":
        payloads = [self.delivery, self.mesa, self.balcao]
        preenchidos = sum(1 for payload in payloads if payload is not None)

        if preenchidos != 1:
            raise ValueError("Exatamente um payload (delivery, mesa ou balcão) deve ser informado.")

        if self.tipo_pedido == TipoPedidoCheckoutEnum.DELIVERY and self.delivery is None:
            raise ValueError("Pedidos do tipo DELIVERY precisam do payload 'delivery'.")
        if self.tipo_pedido == TipoPedidoCheckoutEnum.MESA and self.mesa is None:
            raise ValueError("Pedidos do tipo MESA precisam do payload 'mesa'.")
        if self.tipo_pedido == TipoPedidoCheckoutEnum.BALCAO and self.balcao is None:
            raise ValueError("Pedidos do tipo BALCAO precisam do payload 'balcão'.")

        return self


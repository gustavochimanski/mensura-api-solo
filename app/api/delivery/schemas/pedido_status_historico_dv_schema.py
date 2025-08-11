from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, constr
from .shared_enums_schema import PedidoStatusEnum

class AlterarStatusPedidoRequest(BaseModel):
    pedido_id: int
    status: PedidoStatusEnum
    motivo: Optional[constr(max_length=255)] = None
    criado_por: Optional[constr(max_length=60)] = None

class PedidoStatusHistoricoOut(BaseModel):
    id: int
    pedido_id: int
    status: PedidoStatusEnum
    motivo: Optional[str]
    criado_em: datetime
    criado_por: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class HistoricoDoPedidoResponse(BaseModel):
    pedido_id: int
    historicos: List[PedidoStatusHistoricoOut]

    model_config = ConfigDict(from_attributes=True)

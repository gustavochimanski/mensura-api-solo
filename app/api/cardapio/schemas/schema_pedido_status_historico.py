from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, constr
from app.api.cadastros.schemas.schema_shared_enums import PedidoStatusEnum

class AlterarStatusPedidoRequest(BaseModel):
    pedido_id: int
    status: PedidoStatusEnum
    motivo: Optional[str] = None
    observacoes: Optional[str] = None
    criado_por: Optional[constr(max_length=60)] = None
    ip_origem: Optional[constr(max_length=45)] = None
    user_agent: Optional[constr(max_length=500)] = None

class AlterarStatusPedidoBody(BaseModel):
    status: PedidoStatusEnum
    motivo: Optional[str] = None
    observacoes: Optional[str] = None
    criado_por: Optional[constr(max_length=60)] = None
    ip_origem: Optional[constr(max_length=45)] = None
    user_agent: Optional[constr(max_length=500)] = None

class PedidoStatusHistoricoOut(BaseModel):
    id: int
    pedido_id: int
    status: PedidoStatusEnum
    motivo: Optional[str]
    observacoes: Optional[str]
    criado_em: datetime
    criado_por: Optional[str]
    ip_origem: Optional[str]
    user_agent: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class HistoricoDoPedidoResponse(BaseModel):
    pedido_id: int
    historicos: List[PedidoStatusHistoricoOut]

    model_config = ConfigDict(from_attributes=True)

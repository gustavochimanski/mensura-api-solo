from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional


from pydantic import BaseModel, ConfigDict, Field


class PedidoPendenteAcertoOut(BaseModel):
    id: int
    entregador_id: Optional[int] = None
    valor_total: Optional[float] = None
    data_criacao: datetime
    cliente_id: Optional[int] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class FecharPedidosDiretoRequest(BaseModel):
    empresa_id: int = Field(gt=0)
    inicio: datetime
    fim: datetime
    entregador_id: Optional[int] = Field(default=None, gt=0)
    fechado_por: Optional[str] = None


class FecharPedidosDiretoResponse(BaseModel):
    pedidos_fechados: int
    pedido_ids: List[int] = Field(default_factory=list)
    valor_total: Optional[float] = None
    valor_diaria_total: Optional[float] = None
    valor_liquido: Optional[float] = None
    inicio: datetime
    fim: datetime
    mensagem: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ResumoAcertoEntregador(BaseModel):
    data: date
    entregador_id: int
    entregador_nome: Optional[str] = None
    valor_diaria: Optional[float] = None
    qtd_pedidos: int
    valor_pedidos: float
    valor_liquido: float


class PreviewAcertoResponse(BaseModel):
    empresa_id: int
    inicio: datetime
    fim: datetime
    entregador_id: Optional[int] = None
    resumos: List[ResumoAcertoEntregador] = Field(default_factory=list)
    total_pedidos: int
    total_bruto: float
    total_diarias: float
    total_liquido: float


class AcertosPassadosResponse(BaseModel):
    empresa_id: int
    inicio: datetime
    fim: datetime
    entregador_id: Optional[int] = None
    resumos: List[ResumoAcertoEntregador] = Field(default_factory=list)
    total_pedidos: int
    total_bruto: float
    total_diarias: float
    total_liquido: float



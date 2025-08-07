from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class ItemPedidoRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None


class FinalizarPedidoRequest(BaseModel):
    cliente_id: Optional[int] = None
    empresa_id: int
    endereco_id: Optional[int] = None
    observacao_geral: Optional[str] = None
    itens: List[ItemPedidoRequest]


class ItemPedidoResponse(BaseModel):
    id: int
    produto_cod_barras: str
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PedidoResponse(BaseModel):
    id: int
    cliente_id: Optional[int]
    empresa_id: int
    endereco_id: Optional[int]
    observacao_geral: Optional[str]
    valor_total: float
    data_criacao: datetime
    itens: List[ItemPedidoResponse]

    model_config = ConfigDict(from_attributes=True)


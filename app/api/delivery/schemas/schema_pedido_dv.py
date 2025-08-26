from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, condecimal
from .schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum

class ItemPedidoRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None

class FinalizarPedidoRequest(BaseModel):
    cliente_id: Optional[int] = None
    empresa_id: int
    endereco_id: Optional[int] = None
    tipo_entrega: TipoEntregaEnum = TipoEntregaEnum.DELIVERY
    origem: OrigemPedidoEnum = OrigemPedidoEnum.WEB
    observacao_geral: Optional[str] = None
    cupom_id: Optional[int] = None
    troco_para: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    itens: List[ItemPedidoRequest]

class ItemPedidoResponse(BaseModel):
    id: int
    produto_cod_barras: str
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    # snapshots
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PedidoResponse(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente_id: Optional[int]
    empresa_id: int
    entregador_id: Optional[int]
    endereco_id: Optional[int]
    tipo_entrega: TipoEntregaEnum
    origem: OrigemPedidoEnum

    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float

    previsao_entrega: Optional[datetime] = None
    distancia_km: Optional[float] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    cupom_id: Optional[int] = None

    data_criacao: datetime
    data_atualizacao: datetime

    itens: List[ItemPedidoResponse]

    model_config = ConfigDict(from_attributes=True)

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, condecimal, ConfigDict
from .schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum

class ItemPedidoRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None

class EnderecoPedido(BaseModel):
    rua: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    uf: str
    cep: str

class FinalizarPedidoRequest(BaseModel):
    cliente_number: str  # telefone
    empresa_id: int
    endereco: EnderecoPedido
    tipo_entrega: TipoEntregaEnum = TipoEntregaEnum.DELIVERY
    origem: OrigemPedidoEnum = OrigemPedidoEnum.WEB
    observacao_geral: Optional[str] = None
    cupom_id: Optional[int] = None
    troco_para: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    meio_pagamento: str  # "D" ou "C"
    itens: List[ItemPedidoRequest]

class ItemPedidoResponse(BaseModel):
    id: int
    produto_cod_barras: str
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
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
    meio_pagamento: str

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

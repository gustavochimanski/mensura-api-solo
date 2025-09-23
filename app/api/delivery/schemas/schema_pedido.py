from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, condecimal

from .schema_meio_pagamento import MeioPagamentoResponse
from .schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum
from .schema_cliente import ClienteOut
from .schema_endereco import EnderecoOut
from .schema_entregador import EntregadorOut
from .schema_cupom import CupomOut
from .schema_transacao_pagamento import TransacaoOut
from .schema_pedido_status_historico import PedidoStatusHistoricoOut
from app.api.mensura.schemas.schema_empresa import EmpresaResponse


# ======================================================================
# ============================ ADMIN ===================================
# ======================================================================
class PedidoKanbanResponse(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente_id: int | None = None
    telefone_cliente: str | None = None
    nome_cliente: str | None = None
    valor_total: float
    data_criacao: datetime
    observacao_geral: Optional[str] = None
    endereco_cliente: str | None = None
    meio_pagamento_id: int
    meio_pagamento_descricao: str | None = None  # <- novo campo
    model_config = ConfigDict(from_attributes=True)


class EditarPedidoRequest(BaseModel):
    meio_pagamento_id: Optional[int] = None
    endereco_id: Optional[int] = None
    cupom_id: Optional[int] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[condecimal(max_digits=18, decimal_places=2)] = None

class ItemPedidoEditar(BaseModel):
    id: Optional[int] = None           # ID do item já existente no pedido
    produto_cod_barras: Optional[str] = None  # Apenas para adicionar
    quantidade: Optional[int] = None
    observacao: Optional[str] = None
    acao: str  # "novo-item", "atualizar", "remover"

class VincularEntregadorRequest(BaseModel):
    entregador_id: Optional[int] = None  # None para desvincular, ID para vincular

class ModoEdicaoRequest(BaseModel):
    modo_edicao: bool  # True = modo edição (X), False = editado (D)


# ======================================================================
# ============================ CLIENTE =================================
# ======================================================================
class ItemPedidoRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None

class FinalizarPedidoRequest(BaseModel):
    empresa_id: int
    cliente_id: Optional[str] = None  # agora será setado pelo token
    endereco_id: Optional[int] = None  # Opcional para permitir retirada
    meio_pagamento_id: Optional[int] = None  # Opcional para permitir edição posterior
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
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PedidoResponse(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente_id: Optional[int] = None
    telefone_cliente: Optional[str] = None
    empresa_id: int
    entregador_id: Optional[int]
    endereco_id: Optional[int]
    meio_pagamento_id: Optional[int] = None
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
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    model_config = ConfigDict(from_attributes=True)

class PedidoResponseCompleto(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: Optional[ClienteOut] = None
    empresa_id: int
    entregador_id: Optional[int]
    endereco_id: Optional[int]
    meio_pagamento_id: Optional[int] = None
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
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    model_config = ConfigDict(from_attributes=True)

class PedidoResponseCompletoComEndereco(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: Optional[ClienteOut] = None
    endereco: Optional[EnderecoOut] = None
    empresa_id: int
    entregador_id: Optional[int]
    meio_pagamento_id: Optional[int] = None
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
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    model_config = ConfigDict(from_attributes=True)

class PedidoResponseCompletoTotal(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: Optional[ClienteOut] = None
    endereco: Optional[EnderecoOut] = None
    empresa: Optional[EmpresaResponse] = None
    entregador: Optional[EntregadorOut] = None
    meio_pagamento: Optional[MeioPagamentoResponse] = None
    cupom: Optional[CupomOut] = None
    transacao: Optional[TransacaoOut] = None
    historicos: List[PedidoStatusHistoricoOut] = []
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
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    model_config = ConfigDict(from_attributes=True)


class PedidoResponseSimplificado(BaseModel):
    """Schema simplificado para listagem de pedidos do cliente"""
    id: int
    status: PedidoStatusEnum
    cliente_nome: str
    cliente_telefone: Optional[str] = None
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    previsao_entrega: Optional[datetime] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    endereco_snapshot: Optional[dict] = None
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    meio_pagamento_nome: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
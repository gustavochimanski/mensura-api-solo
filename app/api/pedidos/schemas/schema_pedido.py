"""
Schemas (DTOs) para pedidos unificados.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, constr


class TipoPedidoEnum(str, Enum):
    """Tipos de pedidos suportados."""
    MESA = "MESA"
    BALCAO = "BALCAO"
    DELIVERY = "DELIVERY"


class StatusPedidoEnum(str, Enum):
    """Status de pedidos."""
    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    SAIU_PARA_ENTREGA = "S"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


class TipoEntregaEnum(str, Enum):
    """Tipo de entrega (apenas para delivery)."""
    DELIVERY = "DELIVERY"
    RETIRADA = "RETIRADA"


class OrigemPedidoEnum(str, Enum):
    """Origem do pedido (apenas para delivery)."""
    WEB = "WEB"
    APP = "APP"
    BALCAO = "BALCAO"


class PedidoItemIn(BaseModel):
    """Schema para criar um item de pedido."""
    produto_id: Optional[int] = None
    combo_id: Optional[int] = None
    produto_cod_barras: Optional[str] = None  # Para compatibilidade com balcão
    quantidade: int = Field(ge=1, default=1)
    observacoes: Optional[constr(max_length=500)] = None
    adicionais: Optional[List[int]] = None  # IDs dos adicionais selecionados

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "produto_id": 123,
                    "quantidade": 2,
                    "observacoes": "Sem cebola",
                    "adicionais": [1, 2]
                }
            ]
        }
    )


class PedidoItemOut(BaseModel):
    """Schema de resposta para item de pedido."""
    id: int
    produto_cod_barras: Optional[str] = None
    combo_id: Optional[int] = None
    nome: str
    descricao: Optional[str] = None
    quantidade: int
    preco_unitario: float
    preco_total: float
    observacoes: Optional[str] = None
    adicionais: Optional[str] = None  # JSON serializado

    model_config = ConfigDict(from_attributes=True)


class PedidoCreate(BaseModel):
    """Schema para criar um pedido."""
    tipo_pedido: TipoPedidoEnum = Field(..., description="Tipo do pedido: MESA, BALCAO ou DELIVERY")
    empresa_id: int = Field(..., description="ID da empresa")
    
    # Campos específicos por tipo
    mesa_id: Optional[int] = Field(None, description="ID da mesa (obrigatório para MESA, opcional para BALCAO)")
    cliente_id: Optional[int] = Field(None, description="ID do cliente")
    
    # Campos específicos para DELIVERY
    endereco_id: Optional[int] = Field(None, description="ID do endereço (obrigatório para DELIVERY)")
    entregador_id: Optional[int] = Field(None, description="ID do entregador (apenas para DELIVERY)")
    tipo_entrega: Optional[TipoEntregaEnum] = Field(None, description="Tipo de entrega (apenas para DELIVERY)")
    origem: Optional[OrigemPedidoEnum] = Field(None, description="Origem do pedido (apenas para DELIVERY)")
    
    # Campos gerais
    observacoes: Optional[constr(max_length=500)] = None
    observacao_geral: Optional[constr(max_length=255)] = None
    num_pessoas: Optional[int] = Field(None, ge=1, description="Número de pessoas (apenas para MESA)")
    troco_para: Optional[float] = Field(None, ge=0, description="Troco para (apenas para DELIVERY)")
    
    # Itens do pedido
    itens: Optional[List[PedidoItemIn]] = None
    
    # Descontos e taxas (principalmente para DELIVERY)
    cupom_id: Optional[int] = None
    desconto: Optional[float] = Field(default=0, ge=0, description="Valor do desconto")
    taxa_entrega: Optional[float] = Field(default=0, ge=0, description="Taxa de entrega")
    taxa_servico: Optional[float] = Field(default=0, ge=0, description="Taxa de serviço")
    meio_pagamento_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Pedido de Mesa",
                    "value": {
                        "tipo_pedido": "MESA",
                        "empresa_id": 1,
                        "mesa_id": 5,
                        "cliente_id": 10,
                        "num_pessoas": 4,
                        "observacoes": "Mesa 5",
                        "itens": [
                            {"produto_id": 123, "quantidade": 2}
                        ]
                    }
                },
                {
                    "summary": "Pedido de Balcão",
                    "value": {
                        "tipo_pedido": "BALCAO",
                        "empresa_id": 1,
                        "cliente_id": 10,
                        "observacoes": "Para viagem",
                        "itens": [
                            {"produto_cod_barras": "789...", "quantidade": 1}
                        ]
                    }
                },
                {
                    "summary": "Pedido de Delivery",
                    "value": {
                        "tipo_pedido": "DELIVERY",
                        "empresa_id": 1,
                        "cliente_id": 10,
                        "endereco_id": 20,
                        "tipo_entrega": "DELIVERY",
                        "origem": "APP",
                        "observacao_geral": "Deixar na portaria",
                        "troco_para": 50.00,
                        "itens": [
                            {"produto_id": 123, "quantidade": 2, "adicionais": [1, 2]}
                        ]
                    }
                }
            ]
        }
    )


class PedidoOut(BaseModel):
    """Schema de resposta para pedido."""
    id: int
    tipo_pedido: TipoPedidoEnum
    empresa_id: int
    numero_pedido: str
    status: StatusPedidoEnum
    status_descricao: str
    status_cor: str
    
    # Relacionamentos
    mesa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    endereco_id: Optional[int] = None
    entregador_id: Optional[int] = None
    meio_pagamento_id: Optional[int] = None
    cupom_id: Optional[int] = None
    
    # Campos específicos
    tipo_entrega: Optional[TipoEntregaEnum] = None
    origem: Optional[OrigemPedidoEnum] = None
    observacoes: Optional[str] = None
    observacao_geral: Optional[str] = None
    num_pessoas: Optional[int] = None
    troco_para: Optional[float] = None
    
    # Valores
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    
    # Campos delivery
    previsao_entrega: Optional[datetime] = None
    distancia_km: Optional[float] = None
    acertado_entregador: bool = False
    acertado_entregador_em: Optional[datetime] = None
    
    # Itens
    itens: List[PedidoItemOut] = []
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoUpdate(BaseModel):
    """Schema para atualizar um pedido."""
    status: Optional[StatusPedidoEnum] = None
    observacoes: Optional[constr(max_length=500)] = None
    entregador_id: Optional[int] = None
    meio_pagamento_id: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "PREPARANDO",
                    "observacoes": "Atualização de status"
                }
            ]
        }
    )


class PedidoListResponse(BaseModel):
    """Schema de resposta para listagem de pedidos."""
    total: int
    items: List[PedidoOut]

    model_config = ConfigDict(from_attributes=True)


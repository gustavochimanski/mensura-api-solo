from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, constr


class StatusPedidoBalcaoEnum(str, Enum):
    """Status de pedidos de balcão alinhados ao fluxo de delivery (sem o status 'S')."""

    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


class PedidoBalcaoItemIn(BaseModel):
    produto_cod_barras: constr(min_length=1)
    quantidade: int = Field(ge=1, default=1)
    observacao: Optional[constr(max_length=255)] = None


class PedidoBalcaoCreate(BaseModel):
    empresa_id: int = Field(
        ...,
        description="ID da empresa responsável pelo pedido de balcão."
    )
    mesa_id: Optional[int] = Field(
        None,
        description="Código numérico da mesa (opcional). Se informado, o sistema buscará a mesa pelo código."
    )
    cliente_id: Optional[int] = None
    observacoes: Optional[constr(max_length=500)] = None
    itens: Optional[List[PedidoBalcaoItemIn]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Criar pedido de balcão sem mesa",
                    "value": {
                        "cliente_id": 123,
                        "observacoes": "Para viagem",
                        "itens": [
                            {"produto_cod_barras": "789...", "quantidade": 2}
                        ]
                    }
                },
                {
                    "summary": "Criar pedido de balcão com mesa (opcional)",
                    "value": {
                        "mesa_id": 1,
                        "observacoes": "Balcão",
                        "itens": [
                            {"produto_cod_barras": "123...", "quantidade": 1}
                        ]
                    }
                }
            ]
        }
    )


class PedidoBalcaoItemOut(BaseModel):
    id: int
    produto_cod_barras: str
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PedidoBalcaoOut(BaseModel):
    id: int
    empresa_id: int
    numero_pedido: str
    mesa_id: Optional[int] = None
    cliente_id: Optional[int]
    status: StatusPedidoBalcaoEnum
    status_descricao: str
    observacoes: Optional[str] = None
    valor_total: float
    itens: List[PedidoBalcaoItemOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdicionarItemRequest(PedidoBalcaoItemIn):
    pass


class RemoverItemResponse(BaseModel):
    ok: bool
    pedido_id: int
    valor_total: float


class AtualizarStatusPedidoRequest(BaseModel):
    status: StatusPedidoBalcaoEnum


class FecharContaBalcaoRequest(BaseModel):
    """Payload para fechar a conta do pedido informando pagamento."""
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None


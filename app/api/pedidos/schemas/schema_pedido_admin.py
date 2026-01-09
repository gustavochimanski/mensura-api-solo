from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.api.pedidos.schemas.schema_pedido import (
    EditarPedidoRequest,
    FinalizarPedidoRequest,
    ItemComplementoRequest,
    ItemPedidoRequest,
    MeioPagamentoParcialRequest,
)
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum


class PedidoCreateRequest(FinalizarPedidoRequest):
    """
    Alias semântico para criação de pedidos via camada admin unificada.

    Herdamos `FinalizarPedidoRequest` para reaproveitar validações e estruturas
    (itens, receitas, combos, pagamentos, etc.).
    """

    cliente_id: Optional[int] = Field(
        default=None,
        description="Cliente associado (obrigatório para delivery; opcional para mesa/balcão).",
    )

    @model_validator(mode="after")
    def _coagir_cliente_id(self):
        cliente_id = getattr(self, "cliente_id", None)
        if cliente_id is not None:
            try:
                self.cliente_id = int(cliente_id)
            except (TypeError, ValueError):
                raise ValueError("cliente_id deve ser um inteiro válido.")
        return self


class PedidoUpdateRequest(EditarPedidoRequest):
    """
    Payload unificado para edição parcial de pedidos.

    Estende `EditarPedidoRequest` adicionando campos compartilhados entre
    delivery/mesa/balcão.
    """

    cliente_id: Optional[int] = Field(default=None, description="Reatribui o cliente do pedido.")
    mesa_codigo: Optional[str] = Field(
        default=None, description="Novo código da mesa (quando aplicável a mesa/balcão)."
    )
    num_pessoas: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Atualiza a quantidade de pessoas (mesa).",
    )
    observacoes: Optional[str] = Field(
        default=None, description="Observações para mesa/balcão (campo específico)."
    )
    pagamentos: Optional[List[MeioPagamentoParcialRequest]] = Field(
        default=None,
        description="Lista de meios de pagamento parciais para atualização do pedido.",
    )


class PedidoStatusPatchRequest(BaseModel):
    status: PedidoStatusEnum = Field(description="Novo status do pedido.")


class PedidoObservacaoPatchRequest(BaseModel):
    observacoes: str = Field(..., max_length=500, description="Observação a ser registrada no pedido.")


class PedidoFecharContaRequest(BaseModel):
    """Payload unificado para fechamento de conta."""

    meio_pagamento_id: Optional[int] = Field(
        default=None,
        description="ID do meio de pagamento utilizado no fechamento.",
    )
    troco_para: Optional[float] = Field(
        default=None,
        description="Valor informado para troco (quando aplicável).",
    )


class PedidoItemMutationAction(str, Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"


class PedidoItemMutationRequest(BaseModel):
    acao: PedidoItemMutationAction = Field(description="Ação a ser executada sobre o item.")
    tipo: Optional[TipoEntregaEnum] = Field(
        default=None,
        description="Tipo de pedido (DELIVERY, BALCAO, MESA). Opcional - será detectado automaticamente pelo pedido_id se não informado.",
    )
    item_id: Optional[int] = Field(default=None, description="Identificador do item existente.")
    produto_cod_barras: Optional[str] = Field(
        default=None, description="Código de barras do produto (obrigatório para adicionar item simples)."
    )
    receita_id: Optional[int] = Field(default=None, description="Identificador da receita (suportado em delivery, mesa e balcão).")
    combo_id: Optional[int] = Field(default=None, description="Identificador do combo (suportado em delivery, mesa e balcão).")
    quantidade: Optional[int] = Field(default=None, ge=1, description="Quantidade para adicionar/atualizar.")
    observacao: Optional[str] = Field(default=None, description="Observação livre.")
    complementos: Optional[List[ItemComplementoRequest]] = Field(
        default=None,
        description="Complementos do item com seus adicionais selecionados (suportado em delivery, mesa e balcão).",
    )

    def to_item_pedido_request(self) -> ItemPedidoRequest:
        """Converte dados básicos para `ItemPedidoRequest` quando aplicável."""
        return ItemPedidoRequest(
            produto_cod_barras=self.produto_cod_barras or "",
            quantidade=self.quantidade or 1,
            observacao=self.observacao,
            complementos=self.complementos,
        )


class PedidoEntregadorRequest(BaseModel):
    entregador_id: Optional[int] = Field(
        default=None,
        description="Identificador do entregador; null desvincula.",
    )



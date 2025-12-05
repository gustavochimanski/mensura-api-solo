from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.api.pedidos.schemas.schema_pedido import (
    EditarPedidoRequest,
    FinalizarPedidoRequest,
    ItemAdicionalRequest,
    ItemPedidoRequest,
    MeioPagamentoParcialRequest,
)
from app.api.pedidos.services.service_pedidos_mesa import FecharContaMesaRequest
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum


class PedidoCreateRequest(FinalizarPedidoRequest):
    """
    Alias semântico para criação de pedidos via admin v2.

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


class PedidoFecharContaRequest(FecharContaMesaRequest):
    """Alias semântico reutilizando payload de fechamento de conta da mesa."""


class PedidoItemMutationAction(str, Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    REMOVE = "REMOVE"


class PedidoItemMutationRequest(BaseModel):
    acao: PedidoItemMutationAction = Field(description="Ação a ser executada sobre o item.")
    item_id: Optional[int] = Field(default=None, description="Identificador do item existente.")
    produto_cod_barras: Optional[str] = Field(
        default=None, description="Código de barras do produto (obrigatório para adicionar item simples)."
    )
    receita_id: Optional[int] = Field(default=None, description="Identificador da receita (mesa/balcão).")
    combo_id: Optional[int] = Field(default=None, description="Identificador do combo (mesa/balcão).")
    quantidade: Optional[int] = Field(default=None, ge=1, description="Quantidade para adicionar/atualizar.")
    observacao: Optional[str] = Field(default=None, description="Observação livre.")
    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Adicionais estruturados do item (mesa/balcão).",
    )
    adicionais_ids: Optional[List[int]] = Field(
        default=None,
        description="Lista legada de IDs de adicionais (mesa/balcão).",
    )

    def to_item_pedido_request(self) -> ItemPedidoRequest:
        """Converte dados básicos para `ItemPedidoRequest` quando aplicável."""
        return ItemPedidoRequest(
            produto_cod_barras=self.produto_cod_barras or "",
            quantidade=self.quantidade or 1,
            observacao=self.observacao,
            adicionais=self.adicionais,
            adicionais_ids=self.adicionais_ids,
        )


class PedidoEntregadorRequest(BaseModel):
    entregador_id: Optional[int] = Field(
        default=None,
        description="Identificador do entregador; null desvincula.",
    )



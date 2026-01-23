"""
Schemas (DTOs) do bounded context de Pedidos.
"""

# Exporta todos os schemas de pedidos unificados
from .schema_pedido import (
    # Enums
    TipoPedidoCheckoutEnum,
    # Request schemas
    ItemAdicionalComplementoRequest,
    ItemComplementoRequest,
    ItemPedidoRequest,
    ReceitaPedidoRequest,
    ComboPedidoRequest,
    ProdutosPedidoRequest,
    MeioPagamentoParcialRequest,
    FinalizarPedidoRequest,
    EditarPedidoRequest,
    ItemPedidoEditar,
    ModoEdicaoRequest,
    PreviewCheckoutResponse,
    CheckoutTotalResponse,
    # Response schemas
    ItemPedidoResponse,
    ProdutoPedidoAdicionalOut,
    ProdutoPedidoItemOut,
    ReceitaPedidoOut,
    ComboPedidoOut,
    ProdutosPedidoOut,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoComEndereco,
    PedidoResponseCompletoTotal,
    PedidoResponseSimplificado,
    PedidoKanbanResponse,
    KanbanAgrupadoResponse,
    PedidoPagamentoResumo,
    MeioPagamentoKanbanResponse,
    EnderecoPedidoDetalhe,
)

from .schema_pedido_cliente import PedidoClienteListItem
from .schema_pedido_status_historico import (
    AlterarStatusPedidoRequest,
    AlterarStatusPedidoBody,
    PedidoStatusHistoricoOut,
    HistoricoDoPedidoResponse,
)
from .schema_pedido_admin import (
    PedidoCreateRequest,
    PedidoUpdateRequest,
    PedidoStatusPatchRequest,
    PedidoObservacaoPatchRequest,
    PedidoFecharContaRequest,
    PedidoItemMutationRequest,
    PedidoItemMutationAction,
    PedidoEntregadorRequest,
)

__all__ = [
    # Enums
    "TipoPedidoCheckoutEnum",
    # Request schemas
    "ItemAdicionalComplementoRequest",
    "ItemComplementoRequest",
    "ItemPedidoRequest",
    "ReceitaPedidoRequest",
    "ComboPedidoRequest",
    "ProdutosPedidoRequest",
    "MeioPagamentoParcialRequest",
    "FinalizarPedidoRequest",
    "EditarPedidoRequest",
    "ItemPedidoEditar",
    "ModoEdicaoRequest",
    "PreviewCheckoutResponse",
    "CheckoutTotalResponse",
    # Response schemas
    "ItemPedidoResponse",
    "ProdutoPedidoAdicionalOut",
    "ProdutoPedidoItemOut",
    "ReceitaPedidoOut",
    "ComboPedidoOut",
    "ProdutosPedidoOut",
    "PedidoResponse",
    "PedidoResponseCompleto",
    "PedidoResponseCompletoComEndereco",
    "PedidoResponseCompletoTotal",
    "PedidoResponseSimplificado",
    "PedidoKanbanResponse",
    "KanbanAgrupadoResponse",
    "PedidoPagamentoResumo",
    "MeioPagamentoKanbanResponse",
    "EnderecoPedidoDetalhe",
    "PedidoClienteListItem",
    "AlterarStatusPedidoRequest",
    "AlterarStatusPedidoBody",
    "PedidoStatusHistoricoOut",
    "HistoricoDoPedidoResponse",
    "PedidoCreateRequest",
    "PedidoUpdateRequest",
    "PedidoStatusPatchRequest",
    "PedidoObservacaoPatchRequest",
    "PedidoFecharContaRequest",
    "PedidoItemMutationRequest",
    "PedidoItemMutationAction",
    "PedidoEntregadorRequest",
]


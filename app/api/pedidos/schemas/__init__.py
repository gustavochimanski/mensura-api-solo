"""
Schemas (DTOs) do bounded context de Pedidos.
"""

# Exporta todos os schemas de pedidos unificados
from .schema_pedido import (
    # Enums
    TipoPedidoCheckoutEnum,
    # Request schemas
    ItemAdicionalRequest,
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

__all__ = [
    # Enums
    "TipoPedidoCheckoutEnum",
    # Request schemas
    "ItemAdicionalRequest",
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
]


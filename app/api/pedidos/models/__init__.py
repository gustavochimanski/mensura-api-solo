"""
Models do bounded context de Pedidos.
"""

# Importar apenas os modelos unificados (os antigos serão removidos)
from .model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoPedido,
    StatusPedido,
    TipoEntrega,
    OrigemPedido,
    TipoPedidoEnum,
    StatusPedidoEnum,
    TipoEntregaEnum,
    OrigemPedidoEnum,
)
from .model_pedido_item_unificado import PedidoItemUnificadoModel
from .model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
    TipoOperacaoPedido,
    TipoOperacaoPedidoEnum,
)

# Aliases para compatibilidade durante transição
PedidoModel = PedidoUnificadoModel  # Alias para compatibilidade

__all__ = [
    # Modelos unificados
    "PedidoUnificadoModel",
    "PedidoItemUnificadoModel",
    "PedidoHistoricoUnificadoModel",
    # Enums e tipos
    "TipoPedido",
    "StatusPedido",
    "TipoEntrega",
    "OrigemPedido",
    "TipoPedidoEnum",
    "StatusPedidoEnum",
    "TipoEntregaEnum",
    "OrigemPedidoEnum",
    "TipoOperacaoPedido",
    "TipoOperacaoPedidoEnum",
    # Aliases para compatibilidade (deprecated)
    "PedidoModel",  # Alias para PedidoUnificadoModel
]


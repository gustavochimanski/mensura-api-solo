"""
Models do bounded context de Pedidos.
"""

# Importar apenas os modelos unificados (os antigos serão removidos)
from .model_pedido_unificado import (
    PedidoUnificadoModel,
    StatusPedido,
    TipoEntrega,  # DELIVERY, RETIRADA, BALCAO, MESA
    CanalPedido,  # WEB, APP, BALCAO
    StatusPedidoEnum,
    TipoEntregaEnum,
    CanalPedidoEnum,
)
from .model_pedido_item_unificado import PedidoItemUnificadoModel
from .model_pedido_item_complemento import PedidoItemComplementoModel
from .model_pedido_item_complemento_adicional import PedidoItemComplementoAdicionalModel
from .model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
    TipoOperacaoPedido,
    TipoOperacaoPedidoEnum,
)

__all__ = [
    # Modelos unificados
    "PedidoUnificadoModel",
    "PedidoItemUnificadoModel",
    "PedidoItemComplementoModel",
    "PedidoItemComplementoAdicionalModel",
    "PedidoHistoricoUnificadoModel",
    # Enums e tipos
    "StatusPedido",
    "TipoEntrega",  # DELIVERY, RETIRADA, BALCAO, MESA
    "CanalPedido",  # WEB, APP, BALCAO
    "StatusPedidoEnum",
    "TipoEntregaEnum",
    "CanalPedidoEnum",
    "TipoOperacaoPedido",
    "TipoOperacaoPedidoEnum",
]


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
from .model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
    TipoOperacaoPedido,
    TipoOperacaoPedidoEnum,
)

# Alias apenas para PedidoModel (deprecated, mas mantido por compatibilidade)
PedidoModel = PedidoUnificadoModel

__all__ = [
    # Modelos unificados
    "PedidoUnificadoModel",
    "PedidoItemUnificadoModel",
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
    # Alias para compatibilidade (deprecated)
    "PedidoModel",
]


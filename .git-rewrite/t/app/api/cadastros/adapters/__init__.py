"""Adapters (implementações) dos contratos expostos por Cadastros."""

# Nota: Produto, Combo e Adicional adapters estão no módulo catalogo
# Importe diretamente de app.api.catalogo.adapters se necessário

from .cliente_adapter import ClienteAdapter
from .entregador_adapter import EntregadorAdapter
from .regiao_entrega_adapter import RegiaoEntregaAdapter

__all__ = [
    # De cadastros
    "ClienteAdapter",
    "EntregadorAdapter",
    "RegiaoEntregaAdapter",
]


#
from .router_adicionais import router as router_adicionais
from .router_categorias import router as router_categorias
from .router_clientes import router as router_clientes
from .router_enderecos import router as router_enderecos
from .router_meio_pagamento import router as router_meio_pagamento

__all__ = [
    "router_adicionais",
    "router_categorias",
    "router_clientes",
    "router_enderecos",
    "router_meio_pagamento",
]

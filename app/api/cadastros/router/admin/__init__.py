from .router_categorias import router as router_categorias
from .router_clientes import router as router_clientes
from .router_entregadores import router as router_entregadores
from .router_meio_pagamento import router as router_meio_pagamento
from .router_parceiros import router as router_parceiros
from .router_regiao_entrega import router as router_regiao_entrega
from .router_enderecos import router as router_enderecos
from .router_combos import router as router_combos

__all__ = [
    "router_categorias",
    "router_clientes",
    "router_entregadores",
    "router_meio_pagamento",
    "router_parceiros",
    "router_regiao_entrega",
    "router_enderecos",
    "router_combos",
]

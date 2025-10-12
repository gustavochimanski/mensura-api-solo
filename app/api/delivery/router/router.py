from fastapi import APIRouter, Depends

from app.api.delivery.router import router_home_public, router_printer_public
from app.api.delivery.router.categorias import router_categorias_client
from app.api.delivery.router.clientes import router_clientes_client
from app.api.delivery.router.enderecos import router_enderecos_client
from app.api.delivery.router.meio_pagamento import router_meio_pagamento_client
from app.api.delivery.router.parceiros import router_parceiros_public
from app.api.delivery.router.pagamentos import router_pagamentos_client
from app.api.delivery.router.pedidos import router_pedidos_client
from app.api.delivery.router.categorias import router_categorias_admin
from app.api.delivery.router.clientes import router_clientes_admin
from app.api.delivery.router.cupons import router_cupons_admin
from app.api.delivery.router.enderecos import router_enderecos_admin
from app.api.delivery.router.meio_pagamento import router_meio_pagamento_admin
from app.api.delivery.router import router_entregadores_admin
from app.api.delivery.router import router_regiao_entrega_admin
from app.api.delivery.router import router_vitrines_admin
from app.api.delivery.router.pagamentos import router_pagamentos_admin
from app.api.delivery.router.parceiros import router_parceiros_admin
from app.api.delivery.router.pedidos import router_pedidos_admin
from app.api.delivery.router.produtos import router_produtos_admin
from app.api.delivery.router.pagamentos import router_pagamentos_webhook

api_delivery = APIRouter()

# Routers públicos (sem autenticação)
api_delivery.include_router(router_parceiros_public.router)
api_delivery.include_router(router_printer_public.router)
api_delivery.include_router(router_home_public.router)
api_delivery.include_router(router_pagamentos_webhook.router)

# Routers para clientes (usam super_token)
api_delivery.include_router(router_categorias_client.router)
api_delivery.include_router(router_clientes_client.router)
api_delivery.include_router(router_enderecos_client.router)
api_delivery.include_router(router_meio_pagamento_client.router)
api_delivery.include_router(router_pedidos_client.router)
api_delivery.include_router(router_pagamentos_client.router)

# Routers para admin (usam get_current_user)
api_delivery.include_router(router_categorias_admin.router)
api_delivery.include_router(router_clientes_admin.router)
api_delivery.include_router(router_cupons_admin.router)
api_delivery.include_router(router_enderecos_admin.router)
api_delivery.include_router(router_meio_pagamento_admin.router)
api_delivery.include_router(router_pagamentos_admin.router)
api_delivery.include_router(router_parceiros_admin.router)
api_delivery.include_router(router_pedidos_admin.router)
api_delivery.include_router(router_produtos_admin.router)
api_delivery.include_router(router_entregadores_admin.router)
api_delivery.include_router(router_regiao_entrega_admin.router)
api_delivery.include_router(router_vitrines_admin.router)

from fastapi import APIRouter

from app.api.balcao.router.admin.criar_pedido import router as router_criar_pedido
from app.api.balcao.router.admin.adicionar_item import router as router_adicionar_item
from app.api.balcao.router.admin.adicionar_produto_generico import router as router_adicionar_produto_generico
from app.api.balcao.router.admin.remover_item import router as router_remover_item
from app.api.balcao.router.admin.cancelar_pedido import router as router_cancelar_pedido
from app.api.balcao.router.admin.fechar_conta_pedido import router as router_fechar_conta_pedido
from app.api.balcao.router.admin.abrir_pedido import router as router_abrir_pedido
from app.api.balcao.router.admin.fechar_pedido import router as router_fechar_pedido
from app.api.balcao.router.admin.reabrir_pedido import router as router_reabrir_pedido
from app.api.balcao.router.admin.confirmar_pedido import router as router_confirmar_pedido
from app.api.balcao.router.admin.atualizar_status_pedido import router as router_atualizar_status_pedido
from app.api.balcao.router.admin.get_pedido import router as router_get_pedido
from app.api.balcao.router.admin.list_pedidos_abertos import router as router_list_pedidos_abertos
from app.api.balcao.router.admin.list_pedidos_finalizados import router as router_list_pedidos_finalizados
from app.api.balcao.router.admin.obter_historico_pedido import router as router_obter_historico_pedido
from app.api.balcao.router.client.router_pedidos_balcao_client import router as router_pedidos_balcao_client

api_balcao = APIRouter(
    tags=["API - Balcão"]
)

# Routers para admin (cada um com seu próprio prefixo)
api_balcao.include_router(router_criar_pedido)
api_balcao.include_router(router_adicionar_item)
api_balcao.include_router(router_adicionar_produto_generico)
api_balcao.include_router(router_remover_item)
api_balcao.include_router(router_cancelar_pedido)
api_balcao.include_router(router_fechar_conta_pedido)
api_balcao.include_router(router_abrir_pedido)
api_balcao.include_router(router_fechar_pedido)
api_balcao.include_router(router_reabrir_pedido)
api_balcao.include_router(router_confirmar_pedido)
api_balcao.include_router(router_atualizar_status_pedido)
api_balcao.include_router(router_get_pedido)
api_balcao.include_router(router_list_pedidos_abertos)
api_balcao.include_router(router_list_pedidos_finalizados)
api_balcao.include_router(router_obter_historico_pedido)

# Routers para client
api_balcao.include_router(router_pedidos_balcao_client)


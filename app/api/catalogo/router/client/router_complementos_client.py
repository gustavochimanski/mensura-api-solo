# Este arquivo foi esvaziado pois todos os endpoints de listagem de complementos
# foram movidos para a rota pública (router_complementos_public.py)
# 
# Se houver necessidade de endpoints autenticados específicos para clientes,
# eles podem ser adicionados aqui no futuro.

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/catalogo/client/complementos",
    tags=["Client - Catalogo - Complementos"],
)


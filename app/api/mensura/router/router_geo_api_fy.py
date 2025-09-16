from fastapi import APIRouter, Depends

from app.utils.geopapify_client import GeoapifyClient
from clientes.mensura_api.app.core.admin_dependencies import get_current_user
from clientes.mensura_api.app.core.client_dependecies import get_cliente_by_super_token

router = APIRouter(prefix="/api/mensura/geoapify", tags=["GEOAPIFY"])

@router.get("/search-endereco", dependencies=[Depends(get_current_user)])
async def search_endereco(text: str):
    """
    Busca endereço com validação de CEP.
    Se a query contém um CEP, primeiro consulta o ViaCEP para validar.
    Depois complementa com busca no Geoapify para obter coordenadas.
    """
    geo_api_fy = GeoapifyClient()
    return await geo_api_fy.search_endereco_com_cep(text)


@router.get("/cliente/search-endereco", dependencies=[Depends(get_cliente_by_super_token)])
async def search_endereco(text: str):
    """
    Busca endereço com validação de CEP.
    Se a query contém um CEP, primeiro consulta o ViaCEP para validar.
    Depois complementa com busca no Geoapify para obter coordenadas.
    """
    geo_api_fy = GeoapifyClient()
    return await geo_api_fy.search_endereco_com_cep(text)

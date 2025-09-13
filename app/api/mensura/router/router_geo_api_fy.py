from fastapi import APIRouter

from app.utils.geopapify_client import GeoapifyClient

router = APIRouter(prefix="/api/mensura/geoapify", tags=["GEOAPIFY"])

@router.get("/search-endereco")
async def search_endereco(text: str):
    """
    Busca endereço com validação de CEP.
    Se a query contém um CEP, primeiro consulta o ViaCEP para validar.
    Depois complementa com busca no Geoapify para obter coordenadas.
    """
    geo_api_fy = GeoapifyClient()
    return await geo_api_fy.search_endereco_com_cep(text)

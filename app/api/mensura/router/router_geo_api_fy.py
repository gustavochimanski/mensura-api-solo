from fastapi import APIRouter

from app.utils.geopapify_client import GeoapifyClient

router = APIRouter(prefix="/api/mensura/search-endereco-geoapify", tags=["Busca endereco por texto e retorna todos os campos"])
def search_regiao(text: str):
    geo_api_fy = GeoapifyClient()
    return geo_api_fy.geocode_raw(text)

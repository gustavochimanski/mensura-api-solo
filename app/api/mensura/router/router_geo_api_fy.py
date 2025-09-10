from fastapi import APIRouter

from app.utils.geopapify_client import GeoapifyClient

router = APIRouter(prefix="/api/mensura/geoapify/search-endereco", tags=["GEOAPIFY"])

def search_regiao(text: str):
    geo_api_fy = GeoapifyClient()
    return geo_api_fy.geocode_raw(text)

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.geopapify_client import GeoapifyClient


class GeoapifyMini(BaseModel):
    state: str
    state_code: str
    city: str
    district: str
    suburb: Optional[str] = None
    lat: float
    lon: float
    formatted: str


def to_mini_feature(feature: dict) -> GeoapifyMini:
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [None, None])

    # pega bairro preferencialmente do district, se não usar suburb
    district = props.get("district") or props.get("suburb") or ""

    return GeoapifyMini(
        state=props.get("state", ""),
        state_code=props.get("state_code", ""),
        city=props.get("city", ""),
        district=district,
        suburb=props.get("suburb"),
        lat=coords[1] if len(coords) > 1 else None,
        lon=coords[0] if len(coords) > 0 else None,
        formatted=props.get("formatted", "")
    )

router = APIRouter(prefix="/api/mensura/geoapify", tags=["GEOAPIFY"])
@router.get("/search-endereco")
async def search_regiao(text: str):
    geo_api_fy = GeoapifyClient()
    data = await geo_api_fy.geocode_raw(text)
    if not data or not data.get("features"):
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # mapeia todos os features para objetos mini
    return [to_mini_feature(f) for f in data["features"]]

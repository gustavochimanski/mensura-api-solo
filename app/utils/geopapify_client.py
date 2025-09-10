from pydantic import BaseModel
from typing import Optional, Tuple, Dict, Any, List
import httpx
from app.config import settings
from app.utils.logger import logger

class GeoapifyMini(BaseModel):
    state: str
    state_code: str
    city: str
    district: str
    suburb: Optional[str] = None
    lat: float
    lon: float
    formatted: str

class GeoapifyClient:
    BASE_URL = "https://api.geoapify.com/v1/geocode/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEOAPIFY_KEY

    async def geocode_raw(self, query: str) -> Optional[Dict[str, Any]]:
        """Retorna o JSON completo do Geoapify"""
        logger.info(f"[Geoapify] Consultando (RAW) para: {query}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={"text": query, "apiKey": self.api_key}
                )
            logger.info(f"[Geoapify] Status: {response.status_code}, Response: {response.text}")
            data = response.json()
            if not data.get("features"):
                logger.warning(f"[Geoapify] Nenhuma coordenada encontrada para {query}")
                return None
            return data
        except Exception as e:
            logger.error(f"[Geoapify] Erro ao consultar coordenadas (RAW) para {query}: {e}")
            return None

    async def get_coordinates(self, query: str) -> Tuple[Optional[float], Optional[float]]:
        """Retorna latitude/longitude (primeira feature)"""
        logger.info(f"[Geoapify] Consultando coordenadas para: {query}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={"text": query, "apiKey": self.api_key}
                )
            logger.info(f"[Geoapify] Status: {response.status_code}, Response: {response.text}")
            data = response.json()
            if not data.get("features"):
                logger.warning(f"[Geoapify] Nenhuma coordenada encontrada para {query}")
                return None, None
            coords = data["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]
        except Exception as e:
            logger.error(f"[Geoapify] Erro ao consultar coordenadas para {query}: {e}")
            return None, None

    @staticmethod
    def to_mini_feature(feature: dict) -> GeoapifyMini:
        """Transforma uma feature do Geoapify em objeto mini"""
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
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

    async def geocode_mini(self, query: str) -> Optional[List[GeoapifyMini]]:
        """Retorna a lista de features mapeadas para GeoapifyMini"""
        data = await self.geocode_raw(query)
        if not data or not data.get("features"):
            return None
        return [self.to_mini_feature(f) for f in data["features"]]

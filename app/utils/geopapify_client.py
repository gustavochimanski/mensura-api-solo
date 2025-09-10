from pydantic import BaseModel
from typing import Optional, Tuple, Dict, Any, List
import httpx
from app.config import settings
from app.utils.logger import logger


class GeoapifyMini(BaseModel):
    estado: str
    codigo_estado: str
    cidade: str
    bairro: Optional[str] = None
    distrito: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    cep: Optional[str] = None
    pais: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    endereco_formatado: Optional[str] = None


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
            data = response.json()
            if not data.get("features"):
                return None, None
            coords = data["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]
        except Exception as e:
            logger.error(f"[Geoapify] Erro ao consultar coordenadas para {query}: {e}")
            return None, None

    @staticmethod
    def to_mini_feature(feature: dict) -> GeoapifyMini:
        """Transforma uma feature do Geoapify em objeto GeoapifyMini (traduzido)"""
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [None, None])

        # Tentativa de mapeamento para campos traduzidos
        return GeoapifyMini(
            estado=props.get("state", ""),
            codigo_estado=props.get("state_code", ""),
            cidade=props.get("city", "") or props.get("town", "") or props.get("village", ""),
            bairro=props.get("suburb") or props.get("neighbourhood"),
            distrito=props.get("district"),
            rua=props.get("street"),
            numero=props.get("housenumber"),
            cep=props.get("postcode"),
            pais=props.get("country"),
            latitude=coords[1] if len(coords) > 1 else None,
            longitude=coords[0] if len(coords) > 0 else None,
            endereco_formatado=props.get("formatted")
        )

    async def geocode_mini(self, query: str) -> Optional[List[GeoapifyMini]]:
        """Retorna a lista de features mapeadas para GeoapifyMini"""
        data = await self.geocode_raw(query)
        if not data or not data.get("features"):
            return None
        return [self.to_mini_feature(f) for f in data["features"]]

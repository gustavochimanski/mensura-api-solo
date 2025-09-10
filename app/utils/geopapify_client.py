import httpx
from typing import Optional, Tuple, Dict, Any
from app.config import settings
from app.utils.logger import logger

class GeoapifyClient:
    BASE_URL = "https://api.geoapify.com/v1/geocode/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEOAPIFY_KEY

    async def geocode_raw(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Consulta o Geoapify a partir de um texto livre (endereço, bairro, cidade, etc.)
        e retorna o JSON completo da resposta.
        Retorna None caso não encontre nada ou ocorra erro.
        """
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
        """
        Consulta o Geoapify a partir de um texto livre (endereço, bairro, cidade, etc.)
        e retorna (latitude, longitude).
        Retorna (None, None) caso não encontre coordenadas.
        """
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
            return coords[1], coords[0]  # (lat, lon)

        except Exception as e:
            logger.error(f"[Geoapify] Erro ao consultar coordenadas para {query}: {e}")
            return None, None

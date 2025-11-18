from typing import Optional, Tuple, List, Dict
import httpx
from app.config import settings
from app.utils.logger import logger
from app.api.localizacao.contracts.geolocalizacao_contract import (
    IGeolocalizacaoProvider,
    IDistanciaProvider
)


class GoogleMapsAdapter(IGeolocalizacaoProvider, IDistanciaProvider):
    """Adapter para Google Maps API - implementa geocodificação e cálculo de distância."""
    
    BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
    
    def resolver_coordenadas(self, endereco: str) -> Optional[Tuple[float, float]]:
        """
        Resolve coordenadas latitude/longitude para um endereço usando Google Maps Geocoding API.
        
        Args:
            endereco: Endereço em formato texto
            
        Returns:
            Tupla (latitude, longitude) ou None se não encontrar
        """
        if not self.api_key:
            logger.warning("[GoogleMapsAdapter] API key não configurada")
            return None
            
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.BASE_URL,
                    params={
                        "address": endereco,
                        "key": self.api_key,
                        "region": "br",  # Restringe busca ao Brasil
                        "language": "pt-BR"
                    }
                )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                logger.warning(f"[GoogleMapsAdapter] Nenhum resultado encontrado para {endereco}: {data.get('status')}")
                return None
            
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
        except httpx.HTTPStatusError as e:
            logger.error(f"[GoogleMapsAdapter] Erro HTTP ao consultar coordenadas para {endereco}: Status {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"[GoogleMapsAdapter] Erro ao consultar coordenadas para {endereco}: {e}")
            return None
    
    def calcular_distancia_km(
        self,
        origem: Tuple[float, float],
        destino: Tuple[float, float],
        mode: str = "driving"
    ) -> Optional[float]:
        """
        Calcula distância em km entre dois pontos usando Google Maps Distance Matrix API.
        
        Args:
            origem: Tupla (latitude, longitude) do ponto de origem
            destino: Tupla (latitude, longitude) do ponto de destino
            mode: Modo de transporte (driving, walking, bicycling, transit)
            
        Returns:
            Distância em km ou None se não conseguir calcular
        """
        if not self.api_key:
            logger.warning("[GoogleMapsAdapter] API key não configurada")
            return None
            
        lat1, lon1 = origem
        lat2, lon2 = destino
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return None

        origins = f"{lat1},{lon1}"
        destinations = f"{lat2},{lon2}"

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    self.DISTANCE_MATRIX_URL,
                    params={
                        "origins": origins,
                        "destinations": destinations,
                        "mode": mode,
                        "key": self.api_key,
                        "language": "pt-BR",
                        "units": "metric"
                    }
                )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                logger.warning(f"[GoogleMapsAdapter] Erro ao calcular distância: {data.get('status')}")
                return None
                
            rows = data.get("rows", [])
            if not rows:
                return None
                
            elements = rows[0].get("elements", [])
            if not elements:
                return None
                
            element = elements[0]
            if element.get("status") != "OK":
                logger.warning(f"[GoogleMapsAdapter] Erro no elemento de distância: {element.get('status')}")
                return None
                
            distance = element.get("distance", {}).get("value")  # em metros
            if distance is None:
                return None
                
            return float(distance) / 1000.0  # converte para km
        except httpx.HTTPStatusError as e:
            logger.error(f"[GoogleMapsAdapter] Erro HTTP ao calcular distância: Status {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"[GoogleMapsAdapter] Erro ao calcular distância para {origins} -> {destinations}: {e}")
            return None
    
    def buscar_enderecos(self, texto: str, max_results: int = 5) -> List[Dict]:
        """
        Busca endereços usando Google Maps Geocoding API.
        
        Args:
            texto: Texto para buscar (pode ser parcial)
            max_results: Número máximo de resultados a retornar
            
        Returns:
            Lista de dicionários com informações dos endereços encontrados
        """
        if not self.api_key:
            logger.warning("[GoogleMapsAdapter] API key não configurada")
            return []
            
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.BASE_URL,
                    params={
                        "address": texto,
                        "key": self.api_key,
                        "region": "br",  # Restringe busca ao Brasil
                        "language": "pt-BR"
                    }
                )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                logger.warning(f"[GoogleMapsAdapter] Nenhum resultado encontrado para {texto}: {data.get('status')}")
                return []
            
            resultados = []
            for result in data.get("results", [])[:max_results]:
                location = result["geometry"]["location"]
                endereco_info = {
                    "endereco_completo": result.get("formatted_address", ""),
                    "latitude": location.get("lat"),
                    "longitude": location.get("lng"),
                    "tipos": result.get("types", []),
                    "place_id": result.get("place_id", "")
                }
                resultados.append(endereco_info)
            
            return resultados
        except httpx.HTTPStatusError as e:
            logger.error(f"[GoogleMapsAdapter] Erro HTTP ao buscar endereços para {texto}: Status {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"[GoogleMapsAdapter] Erro ao buscar endereços para {texto}: {e}")
            return []


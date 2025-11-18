from typing import Optional, Tuple, List, Dict
import httpx
from app.config import settings
from app.utils.logger import logger


class GoogleMapsAdapter:
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
                        "region": "br",  # Dá preferência ao Brasil
                        "components": "country:br",  # Restringe busca APENAS ao Brasil
                        "language": "pt-BR"
                    }
                )
            response.raise_for_status()
            data = response.json()
            status_code = data.get("status")
            
            # Tratamento específico para diferentes status da API
            if status_code == "REQUEST_DENIED":
                error_message = data.get("error_message", "Acesso negado")
                
                # Detecta problema específico de restrições de referer
                if "referer restrictions" in error_message.lower():
                    logger.error(
                        f"[GoogleMapsAdapter] Acesso negado pela API do Google Maps para '{endereco}'. "
                        f"PROBLEMA: A API key tem restrições de referer (domínio/URL), mas a Geocoding API não aceita esse tipo de restrição. "
                        f"SOLUÇÃO: No Google Cloud Console, altere as restrições da API key para 'Restrição de IP' ou remova as restrições. "
                        f"Erro completo: {error_message}"
                    )
                else:
                    logger.error(
                        f"[GoogleMapsAdapter] Acesso negado pela API do Google Maps para '{endereco}'. "
                        f"Verifique se a API key está correta e se a Geocoding API está habilitada. "
                        f"Erro: {error_message}"
                    )
                return None
            elif status_code == "OVER_QUERY_LIMIT":
                logger.error(
                    f"[GoogleMapsAdapter] Limite de requisições excedido para '{endereco}'. "
                    f"Verifique a cota da API do Google Maps."
                )
                return None
            elif status_code == "INVALID_REQUEST":
                logger.warning(
                    f"[GoogleMapsAdapter] Requisição inválida para '{endereco}': {data.get('error_message', '')}"
                )
                return None
            elif status_code == "ZERO_RESULTS":
                logger.info(f"[GoogleMapsAdapter] Nenhum resultado encontrado para '{endereco}'")
                return None
            elif status_code != "OK" or not data.get("results"):
                logger.warning(
                    f"[GoogleMapsAdapter] Status inesperado para '{endereco}': {status_code}. "
                    f"Mensagem: {data.get('error_message', 'N/A')}"
                )
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
                        "region": "br",  # Dá preferência ao Brasil
                        "components": "country:br",  # Restringe busca APENAS ao Brasil
                        "language": "pt-BR"
                    }
                )
            response.raise_for_status()
            data = response.json()
            status_code = data.get("status")
            
            # Tratamento específico para diferentes status da API
            if status_code == "REQUEST_DENIED":
                error_message = data.get("error_message", "Acesso negado")
                
                # Detecta problema específico de restrições de referer
                if "referer restrictions" in error_message.lower():
                    logger.error(
                        f"[GoogleMapsAdapter] Acesso negado pela API do Google Maps para '{texto}'. "
                        f"PROBLEMA: A API key tem restrições de referer (domínio/URL), mas a Geocoding API não aceita esse tipo de restrição. "
                        f"SOLUÇÃO: No Google Cloud Console, altere as restrições da API key para 'Restrição de IP' ou remova as restrições. "
                        f"Erro completo: {error_message}"
                    )
                else:
                    logger.error(
                        f"[GoogleMapsAdapter] Acesso negado pela API do Google Maps para '{texto}'. "
                        f"Verifique se a API key está correta e se a Geocoding API está habilitada. "
                        f"Erro: {error_message}"
                    )
                return []
            elif status_code == "OVER_QUERY_LIMIT":
                logger.error(
                    f"[GoogleMapsAdapter] Limite de requisições excedido para '{texto}'. "
                    f"Verifique a cota da API do Google Maps."
                )
                return []
            elif status_code == "INVALID_REQUEST":
                logger.warning(
                    f"[GoogleMapsAdapter] Requisição inválida para '{texto}': {data.get('error_message', '')}"
                )
                return []
            elif status_code == "ZERO_RESULTS":
                logger.info(f"[GoogleMapsAdapter] Nenhum resultado encontrado para '{texto}'")
                return []
            elif status_code != "OK" or not data.get("results"):
                logger.warning(
                    f"[GoogleMapsAdapter] Status inesperado para '{texto}': {status_code}. "
                    f"Mensagem: {data.get('error_message', 'N/A')}"
                )
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


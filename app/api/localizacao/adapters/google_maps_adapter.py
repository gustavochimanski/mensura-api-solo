from typing import Optional, Tuple, List, Dict
import httpx
from app.config import settings
from app.utils.logger import logger


class GoogleMapsAdapter:
    """Adapter para Google Maps API - implementa geocodificação e cálculo de distância."""
    
    BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
    PLACES_AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    
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
        Busca por texto de forma "geral", funcionando para:
        - Endereços (rua/avenida/CEP etc)
        - Estabelecimentos e pontos de referência (POIs) (ex: "motel", "restaurante", "hospital")

        Estratégia automática (sem precisar de parâmetro):
        - Tenta Places Autocomplete com types=address
        - Se não achar, tenta Places Autocomplete com types=establishment
        - Se ainda não achar, faz fallback com Places Text Search (busca geral) e resolve detalhes por place_id
        
        Args:
            texto: Texto para buscar (pode ser parcial)
            max_results: Número máximo de resultados a retornar
            
        Returns:
            Lista de dicionários com informações dos endereços encontrados
        """
        if not self.api_key:
            logger.warning("[GoogleMapsAdapter] API key não configurada")
            return []

        texto_norm = (texto or "").strip()
        if not texto_norm:
            return []

        if max_results < 1:
            max_results = 1
        if max_results > 10:
            # Mantém o mesmo limite dos endpoints atuais (1-10)
            max_results = 10

        def _buscar_details_por_place_ids(place_ids: List[str]) -> List[Dict]:
            resultados: List[Dict] = []
            if not place_ids:
                return resultados
            with httpx.Client(timeout=10.0) as client_details:
                for place_id in place_ids:
                    try:
                        details_response = client_details.get(
                            self.PLACES_DETAILS_URL,
                            params={
                                "place_id": place_id,
                                "key": self.api_key,
                                "language": "pt-BR",
                                "fields": "address_components,formatted_address,geometry,name,types",
                            },
                        )
                        details_response.raise_for_status()
                        details_data = details_response.json()
                        if details_data.get("status") == "OK" and details_data.get("result"):
                            result = details_data.get("result")
                            endereco_info = self._extrair_endereco_formatado(result)
                            # Campos aditivos (não quebram quem espera campos de endereço)
                            endereco_info["place_id"] = place_id
                            endereco_info["nome"] = result.get("name")
                            endereco_info["types"] = result.get("types") or []
                            endereco_info["formatted_address"] = result.get("formatted_address")
                            resultados.append(endereco_info)
                    except Exception as e:
                        logger.warning(f"[GoogleMapsAdapter] Erro ao buscar detalhes do place_id {place_id}: {e}")
                        continue
            return resultados

        def _autocomplete_place_ids(types_value: str) -> Optional[List[str]]:
            """Retorna place_ids ou [] (ZERO_RESULTS) ou None (erro crítico)."""
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.PLACES_AUTOCOMPLETE_URL,
                    params={
                        "input": texto_norm,
                        "key": self.api_key,
                        "components": "country:br",
                        "language": "pt-BR",
                        "types": types_value,
                    },
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
                        f"PROBLEMA: A API key tem restrições de referer (domínio/URL), mas a Places API não aceita esse tipo de restrição. "
                        f"SOLUÇÃO: No Google Cloud Console, altere as restrições da API key para 'Restrição de IP' ou remova as restrições. "
                        f"Erro completo: {error_message}"
                    )
                else:
                    logger.error(
                        f"[GoogleMapsAdapter] Acesso negado pela API do Google Maps para '{texto_norm}'. "
                        f"Verifique se a API key está correta e se a Places API está habilitada. "
                        f"Erro: {error_message}"
                    )
                return None
            elif status_code == "OVER_QUERY_LIMIT":
                logger.error(
                    f"[GoogleMapsAdapter] Limite de requisições excedido para '{texto_norm}'. "
                    f"Verifique a cota da API do Google Maps."
                )
                return None
            elif status_code == "INVALID_REQUEST":
                logger.warning(
                    f"[GoogleMapsAdapter] Requisição inválida para '{texto_norm}': {data.get('error_message', '')}"
                )
                return None
            elif status_code == "ZERO_RESULTS":
                return []
            elif status_code != "OK" or not data.get("predictions"):
                logger.warning(
                    f"[GoogleMapsAdapter] Status inesperado para '{texto_norm}': {status_code}. "
                    f"Mensagem: {data.get('error_message', 'N/A')}"
                )
                return None

            predictions = data.get("predictions", [])[:max_results]
            place_ids = [p.get("place_id") for p in predictions if p.get("place_id")]
            return place_ids

        def _text_search_place_ids() -> Optional[List[str]]:
            """Fallback: busca geral por texto (Text Search). Retorna place_ids, [] ou None (erro crítico)."""
            with httpx.Client(timeout=12.0) as client:
                response = client.get(
                    self.PLACES_TEXT_SEARCH_URL,
                    params={
                        "query": texto_norm,
                        "key": self.api_key,
                        "language": "pt-BR",
                        "region": "br",
                    },
                )
            response.raise_for_status()
            data = response.json()
            status_code = data.get("status")
            if status_code == "ZERO_RESULTS":
                return []
            if status_code == "REQUEST_DENIED":
                logger.error(
                    f"[GoogleMapsAdapter] Acesso negado (Places Text Search) para '{texto_norm}': "
                    f"{data.get('error_message', 'N/A')}"
                )
                return None
            if status_code == "OVER_QUERY_LIMIT":
                logger.error("[GoogleMapsAdapter] Limite de requisições excedido (Places Text Search).")
                return None
            if status_code != "OK":
                logger.warning(
                    f"[GoogleMapsAdapter] Status inesperado (Places Text Search) para '{texto_norm}': {status_code}. "
                    f"Mensagem: {data.get('error_message', 'N/A')}"
                )
                return None
            results = (data.get("results") or [])[:max_results]
            return [r.get("place_id") for r in results if r.get("place_id")]

        try:
            # 1) Endereço
            place_ids = _autocomplete_place_ids("address")
            if place_ids is None:
                return []
            if place_ids:
                return _buscar_details_por_place_ids(place_ids)

            # 2) Estabelecimento/POI
            place_ids = _autocomplete_place_ids("establishment")
            if place_ids is None:
                return []
            if place_ids:
                return _buscar_details_por_place_ids(place_ids)

            # 3) Fallback: busca geral por texto
            place_ids = _text_search_place_ids()
            if place_ids is None:
                return []
            if place_ids:
                return _buscar_details_por_place_ids(place_ids)

            return []
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[GoogleMapsAdapter] Erro HTTP ao buscar endereços/lugares para {texto_norm}: "
                f"Status {e.response.status_code}"
            )
            return []
        except Exception as e:
            logger.error(f"[GoogleMapsAdapter] Erro ao buscar endereços/lugares para {texto_norm}: {e}")
            return []
    
    def _extrair_endereco_formatado(self, result: Dict) -> Dict:
        """
        Extrai e formata os componentes do endereço do Google Maps para o formato esperado pelo front-end.
        
        Args:
            result: Resultado do Google Maps Geocoding API
            
        Returns:
            Dicionário com os campos formatados
        """
        location = result.get("geometry", {}).get("location", {})
        address_components = result.get("address_components", [])
        formatted_address = result.get("formatted_address", "")
        
        # Extrai componentes do endereço
        componentes = {}
        for component in address_components:
            types = component.get("types", [])
            long_name = component.get("long_name", "")
            short_name = component.get("short_name", "")
            
            if "street_number" in types:
                componentes["numero"] = long_name
            elif ("route" in types or "street_address" in types) and "logradouro" not in componentes:
                componentes["logradouro"] = long_name
            elif ("sublocality_level_1" in types or "sublocality" in types or "neighborhood" in types) and "bairro" not in componentes:
                componentes["bairro"] = long_name
            elif "administrative_area_level_2" in types:
                componentes["cidade"] = long_name
            elif "administrative_area_level_1" in types:
                componentes["estado"] = long_name
                componentes["codigo_estado"] = short_name
            elif "postal_code" in types:
                cep = long_name.replace("-", "").replace(" ", "")
                # Formata CEP com hífen: 01310100 -> 01310-100
                if len(cep) == 8:
                    componentes["cep"] = f"{cep[:5]}-{cep[5:]}"
                else:
                    componentes["cep"] = long_name
            elif "country" in types:
                componentes["pais"] = long_name
        
        # Formata o endereco_formatado
        endereco_formatado = self._formatar_endereco(
            logradouro=componentes.get("logradouro"),
            numero=componentes.get("numero"),
            bairro=componentes.get("bairro"),
            cidade=componentes.get("cidade"),
            estado=componentes.get("codigo_estado") or componentes.get("estado"),
            cep=componentes.get("cep"),
            formatted_address=formatted_address
        )
        
        return {
            "estado": componentes.get("estado"),
            "codigo_estado": componentes.get("codigo_estado"),
            "cidade": componentes.get("cidade"),
            "bairro": componentes.get("bairro"),
            "distrito": None,  # Google Maps não retorna distrito separadamente
            "logradouro": componentes.get("logradouro"),
            "numero": componentes.get("numero"),
            "cep": componentes.get("cep"),
            "pais": componentes.get("pais"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "endereco_formatado": endereco_formatado
        }
    
    def _formatar_endereco(
        self,
        logradouro: Optional[str],
        numero: Optional[str],
        bairro: Optional[str],
        cidade: Optional[str],
        estado: Optional[str],
        cep: Optional[str],
        formatted_address: str
    ) -> str:
        """
        Formata o endereço no padrão: "Logradouro, Número - Bairro, Cidade - Estado, CEP"
        
        Se não conseguir montar, usa o formatted_address do Google Maps como fallback.
        """
        # Monta o endereço no formato: "Logradouro, Número - Bairro, Cidade - Estado, CEP"
        # Exemplo: "Avenida Paulista, 1000 - Bela Vista, São Paulo - SP, 01310-100"
        
        partes = []
        
        # Primeira parte: Logradouro e número
        if logradouro:
            if numero:
                partes.append(f"{logradouro}, {numero}")
            else:
                partes.append(logradouro)
        
        # Segunda parte: Bairro, Cidade - Estado
        localizacao = []
        if bairro:
            localizacao.append(bairro)
        
        cidade_estado = []
        if cidade:
            cidade_estado.append(cidade)
        if estado:
            cidade_estado.append(estado)
        
        if cidade_estado:
            localizacao.append(" - ".join(cidade_estado))
        
        if localizacao:
            partes.append(", ".join(localizacao))
        
        # Terceira parte: CEP (separado por vírgula e espaço)
        if cep:
            partes.append(cep)
        
        # Junta tudo: "Parte1 - Parte2, Parte3"
        if partes:
            if len(partes) == 3:
                # Formato completo: "Logradouro, Número - Bairro, Cidade - Estado, CEP"
                return f"{partes[0]} - {partes[1]}, {partes[2]}"
            elif len(partes) == 2:
                # Sem CEP ou sem bairro: "Logradouro, Número - Bairro, Cidade - Estado" ou "Logradouro, Número - CEP"
                return " - ".join(partes)
            else:
                # Apenas uma parte
                return partes[0]
        
        # Fallback: usa o formatted_address do Google Maps
        return formatted_address if formatted_address else "Endereço não disponível"
    
    def geocodificar_reversa(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Geocodificação reversa: converte coordenadas (lat/lng) em endereço usando Google Maps Geocoding API.
        
        Args:
            latitude: Latitude do ponto
            longitude: Longitude do ponto
            
        Returns:
            Dicionário com informações do endereço ou None se não encontrar
        """
        if not self.api_key:
            logger.warning("[GoogleMapsAdapter] API key não configurada")
            return None
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.BASE_URL,
                    params={
                        "latlng": f"{latitude},{longitude}",
                        "key": self.api_key,
                        "region": "br",  # Dá preferência ao Brasil
                        "language": "pt-BR"
                    }
                )
            response.raise_for_status()
            data = response.json()
            status_code = data.get("status")
            
            if status_code == "REQUEST_DENIED":
                error_message = data.get("error_message", "Acesso negado")
                logger.error(
                    f"[GoogleMapsAdapter] Acesso negado na geocodificação reversa para ({latitude}, {longitude}). "
                    f"Erro: {error_message}"
                )
                return None
            elif status_code == "OVER_QUERY_LIMIT":
                logger.error(
                    f"[GoogleMapsAdapter] Limite de requisições excedido na geocodificação reversa."
                )
                return None
            elif status_code == "INVALID_REQUEST":
                logger.warning(
                    f"[GoogleMapsAdapter] Requisição inválida na geocodificação reversa: {data.get('error_message', '')}"
                )
                return None
            elif status_code == "ZERO_RESULTS":
                logger.info(f"[GoogleMapsAdapter] Nenhum resultado encontrado para coordenadas ({latitude}, {longitude})")
                return None
            elif status_code != "OK" or not data.get("results"):
                logger.warning(
                    f"[GoogleMapsAdapter] Status inesperado na geocodificação reversa: {status_code}. "
                    f"Mensagem: {data.get('error_message', 'N/A')}"
                )
                return None
            
            # Pega o primeiro resultado (mais relevante)
            result = data["results"][0]
            endereco_info = self._extrair_endereco_formatado(result)
            
            return endereco_info
        except httpx.HTTPStatusError as e:
            logger.error(f"[GoogleMapsAdapter] Erro HTTP na geocodificação reversa: Status {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"[GoogleMapsAdapter] Erro na geocodificação reversa para ({latitude}, {longitude}): {e}")
            return None


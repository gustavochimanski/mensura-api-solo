from pydantic import BaseModel
from typing import Optional, Tuple, Dict, Any, List
import httpx
from app.config import settings
from app.utils.logger import logger
from app.utils.viacep_client import ViaCepClient, ViaCepResponse


class GeoapifyMini(BaseModel):
    estado: str
    codigo_estado: str
    cidade: str
    bairro: Optional[str] = None
    distrito: Optional[str] = None
    logradouro: Optional[str] = None
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
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "text": query, 
                        "apiKey": self.api_key,
                        "countrycode": "br"  # Restringe busca apenas ao Brasil
                    }
                )
            data = response.json()
            if not data.get("features"):
                return None
            return data
        except Exception as e:
            logger.error(f"[Geoapify] Erro ao consultar coordenadas (RAW) para {query}: {e}")
            return None

    async def get_coordinates(self, query: str) -> Tuple[Optional[float], Optional[float]]:
        """Retorna latitude/longitude (primeira feature)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "text": query, 
                        "apiKey": self.api_key,
                        "countrycode": "br"  # Restringe busca apenas ao Brasil
                    }
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
            logradouro=props.get("street"),
            numero=props.get("housenumber"),
            cep=props.get("postcode"),
            pais=props.get("country"),
            latitude=coords[1] if len(coords) > 1 else None,
            longitude=coords[0] if len(coords) > 0 else None,
            endereco_formatado=props.get("formatted")
        )

    @staticmethod
    def viacep_to_mini(viacep_data: ViaCepResponse) -> GeoapifyMini:
        """Converte dados do ViaCEP para o formato GeoapifyMini"""
        return GeoapifyMini(
            estado=viacep_data.uf or "",
            codigo_estado="",  # ViaCEP não fornece código do estado
            cidade=viacep_data.localidade or "",
            bairro=viacep_data.bairro,
            distrito=None,
            logradouro=viacep_data.logradouro,
            numero=None,
            cep=viacep_data.cep,
            pais="Brasil",
            latitude=None,  # ViaCEP não fornece coordenadas
            longitude=None,
            endereco_formatado=f"{viacep_data.logradouro}, {viacep_data.bairro}, {viacep_data.localidade}/{viacep_data.uf}, {viacep_data.cep}" if viacep_data.logradouro else None
        )

    async def geocode_mini(self, query: str) -> Optional[List[GeoapifyMini]]:
        """Retorna a lista de features mapeadas para GeoapifyMini"""
        data = await self.geocode_raw(query)
        if not data or not data.get("features"):
            return None
        return [self.to_mini_feature(f) for f in data["features"]]

    async def search_endereco_com_cep(self, query: str) -> Optional[List[GeoapifyMini]]:
        """
        Busca endereço com validação de CEP.
        Se a query contém um CEP, primeiro consulta o ViaCEP.
        Depois complementa com busca no Geoapify para obter coordenadas.
        """
        viacep_client = ViaCepClient()
        resultados = []
        
        # Verifica se a query contém um CEP
        cep_encontrado = viacep_client.extrair_cep_da_query(query)
        
        if cep_encontrado:
            # Busca no ViaCEP primeiro
            viacep_data = await viacep_client.buscar_cep(cep_encontrado)
            
            if viacep_data:
                # Converte para formato GeoapifyMini
                resultado_viacep = self.viacep_to_mini(viacep_data)
                resultados.append(resultado_viacep)
                
                # Tenta obter coordenadas do Geoapify usando o endereço completo
                endereco_completo = f"{viacep_data.logradouro}, {viacep_data.bairro}, {viacep_data.localidade}, {viacep_data.uf}"
                geoapify_resultados = await self.geocode_mini(endereco_completo)
                
                if geoapify_resultados:
                    # Atualiza o resultado com coordenadas do Geoapify
                    resultado_viacep.latitude = geoapify_resultados[0].latitude
                    resultado_viacep.longitude = geoapify_resultados[0].longitude
                
                return resultados
        
        # Se não há CEP ou CEP não foi encontrado, usa busca normal do Geoapify
        return await self.geocode_mini(query)

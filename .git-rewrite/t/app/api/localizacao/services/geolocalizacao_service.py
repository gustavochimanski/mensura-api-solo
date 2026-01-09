from typing import Optional
from app.api.localizacao.contracts.geolocalizacao_contract import (
    IGeolocalizacaoService,
    IGeolocalizacaoProvider,
    IDistanciaProvider
)
from app.api.localizacao.models.coordenadas import Coordenadas
from app.api.localizacao.adapters.cache_adapter import CacheAdapter
from app.utils.logger import logger


class GeolocalizacaoService(IGeolocalizacaoService):
    """
    Serviço de geolocalização que combina provedores e cache.
    
    Responsabilidades:
    - Resolver endereços para coordenadas (geocodificação)
    - Calcular distâncias entre pontos
    - Gerenciar cache de coordenadas
    """
    
    def __init__(
        self,
        geocodificacao_provider: IGeolocalizacaoProvider,
        distancia_provider: IDistanciaProvider,
        cache: Optional[CacheAdapter] = None
    ):
        self.geocodificacao_provider = geocodificacao_provider
        self.distancia_provider = distancia_provider
        self.cache = cache or CacheAdapter()
    
    def obter_coordenadas(self, endereco: str, cache_key: Optional[str] = None) -> Optional[Coordenadas]:
        """
        Obtém coordenadas de um endereço com cache.
        
        Args:
            endereco: Endereço em formato texto
            cache_key: Chave opcional para cache (se não fornecido, usa o endereço)
            
        Returns:
            Coordenadas ou None
        """
        key = cache_key or endereco
        
        # Verifica cache
        cached_coords = self.cache.get(key)
        if cached_coords:
            return Coordenadas.from_tuple(cached_coords)
        
        # Resolve coordenadas via provedor
        coords_tuple = self.geocodificacao_provider.resolver_coordenadas(endereco)
        if coords_tuple is None:
            logger.warning(f"[GeolocalizacaoService] Não foi possível resolver coordenadas para: {endereco}")
            return None
        
        # Armazena no cache
        if all(coord is not None for coord in coords_tuple):
            self.cache.set(key, coords_tuple)
        
        return Coordenadas.from_tuple(coords_tuple)
    
    def calcular_distancia(
        self,
        origem: Coordenadas,
        destino: Coordenadas,
        mode: str = "driving"
    ) -> Optional[float]:
        """
        Calcula distância entre duas coordenadas.
        
        Args:
            origem: Coordenadas de origem
            destino: Coordenadas de destino
            mode: Modo de transporte (driving, walking, bicycling, transit)
            
        Returns:
            Distância em km ou None
        """
        if origem is None or destino is None:
            logger.warning("[GeolocalizacaoService] Coordenadas ausentes para cálculo de distância")
            return None
        
        origem_tuple = origem.to_tuple()
        destino_tuple = destino.to_tuple()
        
        distancia = self.distancia_provider.calcular_distancia_km(
            origem_tuple,
            destino_tuple,
            mode=mode
        )
        
        if distancia is None:
            logger.warning(
                f"[GeolocalizacaoService] Não foi possível calcular distância entre "
                f"origem={origem_tuple} destino={destino_tuple}"
            )
        
        return distancia
    
    def limpar_cache(self, cache_key: Optional[str] = None):
        """
        Limpa o cache de coordenadas.
        
        Args:
            cache_key: Chave específica para limpar, ou None para limpar tudo
        """
        self.cache.clear(cache_key)
        logger.info(f"[GeolocalizacaoService] Cache limpo: {'chave específica' if cache_key else 'tudo'}")


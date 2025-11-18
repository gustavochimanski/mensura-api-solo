from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.api.localizacao.models.coordenadas import Coordenadas


class IGeolocalizacaoProvider(ABC):
    """Interface para provedores de geolocalização (Google Maps, Geoapify, etc)."""
    
    @abstractmethod
    def resolver_coordenadas(self, endereco: str) -> Optional[Tuple[float, float]]:
        """
        Resolve coordenadas latitude/longitude para um endereço.
        
        Args:
            endereco: Endereço em formato texto
            
        Returns:
            Tupla (latitude, longitude) ou None se não encontrar
        """
        pass


class IDistanciaProvider(ABC):
    """Interface para provedores de cálculo de distância."""
    
    @abstractmethod
    def calcular_distancia_km(
        self,
        origem: Tuple[float, float],
        destino: Tuple[float, float],
        mode: str = "driving"
    ) -> Optional[float]:
        """
        Calcula distância em km entre dois pontos.
        
        Args:
            origem: Tupla (latitude, longitude) do ponto de origem
            destino: Tupla (latitude, longitude) do ponto de destino
            mode: Modo de transporte (driving, walking, bicycling, transit)
            
        Returns:
            Distância em km ou None se não conseguir calcular
        """
        pass


class IGeolocalizacaoService(ABC):
    """Interface para serviço de geolocalização que combina provedores."""
    
    @abstractmethod
    def obter_coordenadas(self, endereco: str, cache_key: Optional[str] = None) -> Optional[Coordenadas]:
        """
        Obtém coordenadas de um endereço com cache.
        
        Args:
            endereco: Endereço em formato texto
            cache_key: Chave opcional para cache (se não fornecido, usa o endereço)
            
        Returns:
            Coordenadas ou None
        """
        pass
    
    @abstractmethod
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
            mode: Modo de transporte
            
        Returns:
            Distância em km ou None
        """
        pass
    
    @abstractmethod
    def limpar_cache(self, cache_key: Optional[str] = None):
        """Limpa o cache de coordenadas."""
        pass


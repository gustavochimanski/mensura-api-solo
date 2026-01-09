from typing import Optional, List, Tuple, TypeVar
from app.api.localizacao.contracts.geolocalizacao_contract import IGeolocalizacaoService
from app.api.localizacao.models.coordenadas import Coordenadas
from app.utils.logger import logger


T = TypeVar('T')


class ProximidadeService:
    """
    Serviço para encontrar entidades mais próximas de um ponto.
    
    Responsabilidades:
    - Encontrar empresa mais próxima de um endereço
    - Filtrar entidades por distância máxima
    - Ordenar por proximidade
    """
    
    def __init__(self, geolocalizacao_service: IGeolocalizacaoService):
        self.geo_service = geolocalizacao_service
    
    def encontrar_mais_proximo(
        self,
        destino: Coordenadas,
        candidatos: List[Tuple[T, Coordenadas]]
    ) -> Optional[Tuple[T, float]]:
        """
        Encontra a entidade mais próxima de um destino.
        
        Args:
            destino: Coordenadas do destino
            candidatos: Lista de tuplas (entidade, coordenadas)
            
        Returns:
            Tupla (entidade, distância_km) ou None se não encontrar
        """
        if not candidatos:
            return None
        
        melhor_entidade = None
        menor_distancia = None
        
        for entidade, origem_coords in candidatos:
            if origem_coords is None:
                continue
            
            distancia = self.geo_service.calcular_distancia(origem_coords, destino)
            if distancia is None:
                continue
            
            if menor_distancia is None or distancia < menor_distancia:
                menor_distancia = distancia
                melhor_entidade = entidade
        
        if melhor_entidade is None:
            logger.warning("[ProximidadeService] Nenhuma entidade próxima encontrada")
            return None
        
        return melhor_entidade, menor_distancia
    
    def filtrar_por_distancia_maxima(
        self,
        origem: Coordenadas,
        candidatos: List[Tuple[T, Coordenadas]],
        distancia_maxima_km: float
    ) -> List[Tuple[T, float]]:
        """
        Filtra entidades dentro de uma distância máxima.
        
        Args:
            origem: Coordenadas de origem
            candidatos: Lista de tuplas (entidade, coordenadas)
            distancia_maxima_km: Distância máxima em km
            
        Returns:
            Lista de tuplas (entidade, distância_km) ordenadas por proximidade
        """
        resultados = []
        
        for entidade, destino_coords in candidatos:
            if destino_coords is None:
                continue
            
            distancia = self.geo_service.calcular_distancia(origem, destino_coords)
            if distancia is None:
                continue
            
            if distancia <= distancia_maxima_km:
                resultados.append((entidade, distancia))
        
        # Ordena por distância (mais próximo primeiro)
        resultados.sort(key=lambda x: x[1])
        
        return resultados


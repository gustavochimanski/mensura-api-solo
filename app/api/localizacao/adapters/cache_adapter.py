from typing import Optional, Dict, Tuple
from threading import Lock
from app.api.localizacao.models.coordenadas import Coordenadas


class CacheAdapter:
    """Adapter para cache de coordenadas em memória."""
    
    def __init__(self):
        self._cache_coordenadas: Dict[str, Tuple[float, float]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Tuple[float, float]]:
        """Obtém coordenadas do cache."""
        with self._lock:
            return self._cache_coordenadas.get(key)
    
    def set(self, key: str, coordenadas: Tuple[float, float]):
        """Armazena coordenadas no cache."""
        with self._lock:
            self._cache_coordenadas[key] = coordenadas
    
    def clear(self, key: Optional[str] = None):
        """Limpa o cache. Se key for fornecido, remove apenas essa entrada."""
        with self._lock:
            if key:
                self._cache_coordenadas.pop(key, None)
            else:
                self._cache_coordenadas.clear()
    
    def has(self, key: str) -> bool:
        """Verifica se existe no cache."""
        with self._lock:
            return key in self._cache_coordenadas


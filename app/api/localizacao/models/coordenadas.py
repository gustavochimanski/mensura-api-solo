from pydantic import BaseModel
from typing import Optional, Tuple


class Coordenadas(BaseModel):
    """Value Object para representar coordenadas geográficas."""
    latitude: float
    longitude: float
    
    def to_tuple(self) -> Tuple[float, float]:
        """Converte para tupla (latitude, longitude)."""
        return (self.latitude, self.longitude)
    
    @classmethod
    def from_tuple(cls, coords: Tuple[Optional[float], Optional[float]]) -> Optional["Coordenadas"]:
        """Cria a partir de uma tupla (latitude, longitude)."""
        if coords[0] is None or coords[1] is None:
            return None
        return cls(latitude=coords[0], longitude=coords[1])
    
    @classmethod
    def from_optional_tuple(cls, coords: Optional[Tuple[Optional[float], Optional[float]]]) -> Optional["Coordenadas"]:
        """Cria a partir de uma tupla opcional."""
        if coords is None:
            return None
        return cls.from_tuple(coords)


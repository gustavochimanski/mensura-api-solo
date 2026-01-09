from abc import ABC, abstractmethod
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel


class RegiaoEntregaDTO(BaseModel):
    """DTO de região de entrega por distância."""
    id: int
    empresa_id: int
    distancia_max_km: Optional[Decimal] = None
    taxa_entrega: Decimal
    ativo: bool
    tempo_estimado_min: Optional[int] = None


class IRegiaoEntregaContract(ABC):
    """Contrato para acesso a faixas/regiões de entrega do contexto Cadastros."""

    @abstractmethod
    def obter_regiao_por_distancia(self, empresa_id: int, distancia_km: Decimal) -> Optional[RegiaoEntregaDTO]:
        raise NotImplementedError



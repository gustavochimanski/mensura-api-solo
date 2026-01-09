from abc import ABC, abstractmethod
from typing import Optional, Tuple

from pydantic import BaseModel


class EmpresaDTO(BaseModel):
    """DTO de empresa para comunicação entre contextos."""
    id: int
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    slug: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class IEmpresaContract(ABC):
    """Contrato para acesso a empresas do domínio Empresas."""

    @abstractmethod
    def obter_empresa(self, empresa_id: int) -> Optional[EmpresaDTO]:
        """Obtém empresa por ID."""
        raise NotImplementedError

    @abstractmethod
    def obter_coordenadas_empresa(self, empresa_id: int) -> Optional[Tuple[float, float]]:
        """Obtém coordenadas (lat, lon) da empresa."""
        raise NotImplementedError



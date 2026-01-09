from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class ClienteDTO(BaseModel):
    """DTO de cliente para comunicação entre contextos."""
    id: int
    nome: str
    telefone: str
    cpf: Optional[str] = None
    email: Optional[str] = None
    ativo: bool


class EnderecoDTO(BaseModel):
    """DTO de endereço de cliente."""
    id: int
    cliente_id: int
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_principal: bool = False


class IClienteContract(ABC):
    """Contrato para acesso a clientes do contexto Cadastros."""

    @abstractmethod
    def obter_cliente(self, cliente_id: int) -> Optional[ClienteDTO]:
        raise NotImplementedError

    @abstractmethod
    def obter_endereco_principal(self, cliente_id: int) -> Optional[EnderecoDTO]:
        raise NotImplementedError



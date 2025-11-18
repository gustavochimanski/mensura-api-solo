from abc import ABC, abstractmethod
from typing import Optional, List

from pydantic import BaseModel


class EntregadorDTO(BaseModel):
    """DTO de entregador para comunicação entre contextos."""
    id: int
    nome: str
    telefone: Optional[str] = None


class IEntregadorContract(ABC):
    """Contrato para acesso a entregadores do contexto Cadastros."""

    @abstractmethod
    def obter_entregador(self, entregador_id: int) -> Optional[EntregadorDTO]:
        raise NotImplementedError

    @abstractmethod
    def listar_por_empresa(self, empresa_id: int) -> List[EntregadorDTO]:
        """Lista entregadores vinculados a uma empresa (quando disponível)."""
        raise NotImplementedError



from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel


class AdicionalDTO(BaseModel):
    """DTO para produtos adicionais dentro de complementos."""
    id: int
    nome: str
    preco: Decimal
    ordem: int


class ComplementoDTO(BaseModel):
    """DTO para complementos com seus adicionais."""
    id: int
    nome: str
    descricao: Optional[str]
    obrigatorio: bool
    quantitativo: bool
    permite_multipla_escolha: bool
    ordem: int
    adicionais: List[AdicionalDTO]


class IComplementoContract(ABC):
    """Contrato para acesso a complementos."""

    @abstractmethod
    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        """Lista todos os complementos vinculados a um produto, com seus adicionais."""
        raise NotImplementedError

    @abstractmethod
    def buscar_por_ids_para_produto(self, cod_barras: str, complemento_ids: List[int]) -> List[ComplementoDTO]:
        """Retorna apenas complementos cujo ID está no array e que estejam vinculados ao produto."""
        raise NotImplementedError

    @abstractmethod
    def buscar_por_ids(self, empresa_id: int, complemento_ids: List[int]) -> List[ComplementoDTO]:
        """Retorna complementos por IDs diretamente (sem precisar de código de barras)."""
        raise NotImplementedError


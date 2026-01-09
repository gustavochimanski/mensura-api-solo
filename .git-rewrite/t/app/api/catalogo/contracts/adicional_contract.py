from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel


class AdicionalDTO(BaseModel):
    id: int
    nome: str
    preco: Decimal
    obrigatorio: bool
    permite_multipla_escolha: bool


class IAdicionalContract(ABC):
    """Contrato para acesso a adicionais."""

    @abstractmethod
    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[AdicionalDTO]:
        raise NotImplementedError

    @abstractmethod
    def buscar_por_ids_para_produto(self, cod_barras: str, adicional_ids: List[int]) -> List[AdicionalDTO]:
        """Retorna apenas adicionais cujo ID está no array e que estejam vinculados ao produto."""
        raise NotImplementedError


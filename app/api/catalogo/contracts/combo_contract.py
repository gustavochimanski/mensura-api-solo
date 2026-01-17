from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
from decimal import Decimal
from pydantic import BaseModel


class ComboItemDTO(BaseModel):
    produto_cod_barras: str | None = None
    receita_id: int | None = None
    quantidade: int


class ComboMiniDTO(BaseModel):
    id: int
    empresa_id: int
    titulo: str
    preco_total: Decimal
    ativo: bool
    itens: List[ComboItemDTO]


class IComboContract(ABC):
    """Contrato para acesso a combos do contexto Catalogo."""

    @abstractmethod
    def buscar_por_id(self, combo_id: int) -> ComboMiniDTO | None:
        raise NotImplementedError


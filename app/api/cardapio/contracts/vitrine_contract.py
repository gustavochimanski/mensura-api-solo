from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel


class ComboVitrineDTO(BaseModel):
    id: int
    empresa_id: int
    titulo: str
    descricao: str
    preco_total: Decimal
    imagem: Optional[str] = None
    ativo: bool
    vitrine_id: Optional[int] = None


class ReceitaVitrineDTO(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_venda: Decimal
    imagem: Optional[str] = None
    ativo: bool
    disponivel: bool
    vitrine_id: Optional[int] = None


class IVitrineContract(ABC):
    """Contrato para acesso a vitrines e seus vínculos (combos e receitas)."""

    @abstractmethod
    def listar_combos_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> dict[int, List[ComboVitrineDTO]]:
        """
        Retorna um dicionário {vitrine_id: [ComboVitrineDTO, ...]} 
        com os combos vinculados às vitrines especificadas.
        """
        raise NotImplementedError

    @abstractmethod
    def listar_receitas_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> dict[int, List[ReceitaVitrineDTO]]:
        """
        Retorna um dicionário {vitrine_id: [ReceitaVitrineDTO, ...]} 
        com as receitas vinculadas às vitrines especificadas.
        """
        raise NotImplementedError

    @abstractmethod
    def listar_combos_por_vitrine_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> dict[int, List[ComboVitrineDTO]]:
        """
        Retorna um dicionário {vitrine_id: [ComboVitrineDTO, ...]} 
        com os combos vinculados às vitrines de uma categoria específica.
        """
        raise NotImplementedError

    @abstractmethod
    def listar_receitas_por_vitrine_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> dict[int, List[ReceitaVitrineDTO]]:
        """
        Retorna um dicionário {vitrine_id: [ReceitaVitrineDTO, ...]} 
        com as receitas vinculadas às vitrines de uma categoria específica.
        """
        raise NotImplementedError


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
    imagem: Optional[str] = None


class ComplementoDTO(BaseModel):
    """DTO para complementos com seus adicionais.
    
    Nota: obrigatorio, quantitativo, minimo_itens e maximo_itens vêm da vinculação,
    não mais do complemento em si.
    """
    id: int
    nome: str
    descricao: Optional[str]
    obrigatorio: bool  # Da vinculação
    quantitativo: bool  # Da vinculação
    minimo_itens: Optional[int] = None  # Da vinculação
    maximo_itens: Optional[int] = None  # Da vinculação
    ordem: int  # Da vinculação
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
    
    def listar_por_receita(self, receita_id: int, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        """Lista todos os complementos vinculados a uma receita, com seus adicionais."""
        # Método opcional - não é abstrato para manter compatibilidade
        # Implementações devem fornecer este método se quiserem suportar receitas
        return []
    
    def listar_por_combo(self, combo_id: int, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        """Lista todos os complementos vinculados a um combo, com seus adicionais."""
        # Método opcional - não é abstrato para manter compatibilidade
        # Implementações devem fornecer este método se quiserem suportar combos
        return []


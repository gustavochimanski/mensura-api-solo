from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel


class ProdutoIngredienteDTO(BaseModel):
    id: int
    produto_cod_barras: str
    ingrediente_cod_barras: str
    quantidade: Optional[float] = None
    unidade: Optional[str] = None


class ProdutoAdicionalDTO(BaseModel):
    id: int
    produto_cod_barras: str
    adicional_cod_barras: str
    preco: Optional[Decimal] = None


class ReceitaMiniDTO(BaseModel):
    id: int
    empresa_id: int
    nome: str
    preco_venda: Decimal
    ativo: bool
    disponivel: bool


class IReceitasContract(ABC):
    """Contrato para acesso ao contexto de Receitas (ingredientes e adicionais por produto)."""

    @abstractmethod
    def listar_ingredientes_por_produto(self, produto_cod_barras: str) -> List[ProdutoIngredienteDTO]:
        raise NotImplementedError

    @abstractmethod
    def listar_adicionais_por_produto(self, produto_cod_barras: str) -> List[ProdutoAdicionalDTO]:
        raise NotImplementedError

    @abstractmethod
    def obter_receita_por_id(self, receita_id: int) -> Optional[ReceitaMiniDTO]:
        """Obtém uma receita por ID."""
        raise NotImplementedError


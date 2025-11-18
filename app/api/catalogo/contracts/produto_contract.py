from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel


class ProdutoDTO(BaseModel):
    """DTO de produto para comunicação entre contextos (chave por código de barras)."""
    cod_barras: str
    descricao: str
    ativo: bool
    imagem: Optional[str] = None
    unidade_medida: Optional[str] = None


class ProdutoEmpDTO(BaseModel):
    """DTO de configuração do produto por empresa."""
    empresa_id: int
    cod_barras: str
    preco_venda: Decimal
    disponivel: bool
    exibir_delivery: bool
    produto: Optional[ProdutoDTO] = None


class IProdutoContract(ABC):
    """Contrato para acesso a produtos do contexto Catalogo."""

    @abstractmethod
    def obter_produto_emp_por_cod(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpDTO]:
        """Obtém configuração de produto da empresa por código de barras."""
        raise NotImplementedError

    @abstractmethod
    def validar_produto_disponivel(self, empresa_id: int, cod_barras: str, quantidade: int = 1) -> bool:
        """Valida se produto está disponível para venda (estoque/flags quando aplicável)."""
        raise NotImplementedError

    @abstractmethod
    def listar_produtos_ativos_da_empresa(self, empresa_id: int, apenas_delivery: bool = True) -> List[ProdutoDTO]:
        """Lista produtos ativos da empresa."""
        raise NotImplementedError


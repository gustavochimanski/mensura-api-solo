"""
Schemas para busca global de produtos, receitas e combos
"""
from typing import Optional, Literal
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ItemBuscaGlobalOut(BaseModel):
    """Item de produto normal na busca global"""
    tipo: Literal["produto"] = "produto"
    id: str  # código de barras
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    preco_venda: float
    disponivel: bool
    ativo: bool
    empresa_id: int
    
    model_config = ConfigDict(from_attributes=True)


class ReceitaBuscaGlobalOut(BaseModel):
    """Item de receita na busca global"""
    tipo: Literal["receita"] = "receita"
    id: int
    receita_id: int  # alias para id
    nome: str
    descricao: Optional[str] = None
    imagem: Optional[str] = None
    preco_venda: float
    disponivel: bool
    ativo: bool
    empresa_id: int
    
    model_config = ConfigDict(from_attributes=True)


class ComboBuscaGlobalOut(BaseModel):
    """Item de combo na busca global"""
    tipo: Literal["combo"] = "combo"
    id: int
    combo_id: int  # alias para id
    titulo: str
    descricao: str
    imagem: Optional[str] = None
    preco_total: float
    ativo: bool
    empresa_id: int
    
    model_config = ConfigDict(from_attributes=True)


class BuscaGlobalItemOut(BaseModel):
    """
    Item unificado da busca global.
    Pode ser produto, receita ou combo.
    """
    tipo: Literal["produto", "receita", "combo"]
    
    # Campos comuns
    id: str | int  # código de barras para produtos, ID para receitas/combos
    nome: str  # descricao para produtos, nome para receitas, titulo para combos
    descricao: Optional[str] = None
    imagem: Optional[str] = None
    preco: float  # preco_venda para produtos/receitas, preco_total para combos
    disponivel: Optional[bool] = None  # None para combos (não tem campo disponivel)
    ativo: bool
    empresa_id: int
    
    # Campos específicos (opcionais para facilitar uso no frontend)
    cod_barras: Optional[str] = None  # Apenas para produtos
    receita_id: Optional[int] = None  # Apenas para receitas
    combo_id: Optional[int] = None  # Apenas para combos
    preco_venda: Optional[float] = None  # Para produtos/receitas
    preco_total: Optional[float] = None  # Para combos
    titulo: Optional[str] = None  # Para combos
    
    model_config = ConfigDict(from_attributes=True)


class BuscaGlobalResponse(BaseModel):
    """Resposta da busca global"""
    produtos: list[BuscaGlobalItemOut] = Field(default_factory=list)
    receitas: list[BuscaGlobalItemOut] = Field(default_factory=list)
    combos: list[BuscaGlobalItemOut] = Field(default_factory=list)
    total: int = Field(description="Total de resultados encontrados")
    
    model_config = ConfigDict(from_attributes=True)


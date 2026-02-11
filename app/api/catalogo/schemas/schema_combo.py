"""
Schemas de Combos
Centralizado no schema de catalogo
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, condecimal, constr, model_validator


class ComboSecaoItemIn(BaseModel):
    produto_cod_barras: Optional[constr(min_length=1)] = None
    receita_id: Optional[int] = None
    preco_incremental: condecimal(max_digits=18, decimal_places=2) = Field(..., ge=0)
    permite_quantidade: bool = False
    quantidade_min: int = Field(ge=1, default=1)
    quantidade_max: int = Field(ge=1, default=1)

    @model_validator(mode='after')
    def validate_exactly_one(self):
        has_produto = self.produto_cod_barras is not None
        has_receita = self.receita_id is not None
        if not (has_produto or has_receita):
            raise ValueError("Deve fornecer produto_cod_barras ou receita_id")
        if has_produto and has_receita:
            raise ValueError("Deve fornecer apenas um: produto_cod_barras ou receita_id")
        if not self.permite_quantidade and (self.quantidade_min != 1 or self.quantidade_max != 1):
            raise ValueError("quantidade_min/max só podem ser diferentes de 1 quando permite_quantidade=True")
        if self.quantidade_min > self.quantidade_max:
            raise ValueError("quantidade_min não pode ser maior que quantidade_max")
        return self


class ComboSecaoIn(BaseModel):
    titulo: constr(min_length=1, max_length=120)
    descricao: Optional[constr(min_length=1, max_length=255)] = None
    obrigatorio: bool = False
    quantitativo: bool = False
    minimo_itens: int = Field(ge=0, default=0)
    maximo_itens: int = Field(ge=1, default=1)
    itens: List[ComboSecaoItemIn] = Field(min_length=1)

class CriarComboRequest(BaseModel):
    empresa_id: int
    titulo: constr(min_length=1, max_length=120)
    descricao: Optional[constr(min_length=1, max_length=255)] = None
    preco_total: condecimal(max_digits=18, decimal_places=2) = Field(..., ge=0)
    custo_total: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: bool = True
    secoes: List[ComboSecaoIn] = Field(min_length=1, description="Lista de seções do combo")


class AtualizarComboRequest(BaseModel):
    titulo: Optional[constr(min_length=1, max_length=120)] = None
    descricao: Optional[constr(min_length=1, max_length=255)] = None
    preco_total: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo_total: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: Optional[bool] = None
    secoes: Optional[List[ComboSecaoIn]] = Field(default=None, description="Substitui todas as seções do combo")


class ComboSecaoItemDTO(BaseModel):
    id: int
    produto_cod_barras: Optional[str] = None
    receita_id: Optional[int] = None
    preco_incremental: float
    permite_quantidade: bool
    quantidade_min: int
    quantidade_max: int
    ordem: int

    model_config = ConfigDict(from_attributes=True)


class ComboSecaoDTO(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    obrigatorio: bool
    quantitativo: bool
    minimo_itens: int
    maximo_itens: int
    itens: List[ComboSecaoItemDTO]
    ordem: int

    model_config = ConfigDict(from_attributes=True)

class ComboDTO(BaseModel):
    id: int
    empresa_id: int
    titulo: str
    descricao: str
    preco_total: float
    custo_total: Optional[float] = None
    ativo: bool
    imagem: Optional[str] = None
    secoes: List[ComboSecaoDTO]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListaCombosResponse(BaseModel):
    data: List[ComboDTO]
    total: int
    page: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)


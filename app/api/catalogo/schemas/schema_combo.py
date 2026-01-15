"""
Schemas de Combos
Centralizado no schema de catalogo
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, condecimal, constr, model_validator


class ComboItemIn(BaseModel):
    """
    Schema para item de combo.
    
    Deve fornecer exatamente um dos seguintes:
    - produto_cod_barras: para vincular um produto normal
    - receita_id: para vincular uma receita
    """
    produto_cod_barras: Optional[constr(min_length=1)] = None
    receita_id: Optional[int] = None
    quantidade: int = Field(ge=1, default=1)
    
    @model_validator(mode='after')
    def validate_exactly_one(self):
        """Valida que exatamente um dos campos seja fornecido"""
        has_produto = self.produto_cod_barras is not None
        has_receita = self.receita_id is not None
        
        if not (has_produto or has_receita):
            raise ValueError("Deve fornecer produto_cod_barras ou receita_id")
        if has_produto and has_receita:
            raise ValueError("Deve fornecer apenas um: produto_cod_barras ou receita_id")
        
        return self


class CriarComboRequest(BaseModel):
    empresa_id: int
    titulo: constr(min_length=1, max_length=120)
    descricao: constr(min_length=1, max_length=255)
    preco_total: condecimal(max_digits=18, decimal_places=2) = Field(..., ge=0)
    custo_total: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: bool = True
    itens: List[ComboItemIn] = Field(min_length=1, description="Lista de itens do combo")


class AtualizarComboRequest(BaseModel):
    titulo: Optional[constr(min_length=1, max_length=120)] = None
    descricao: Optional[constr(min_length=1, max_length=255)] = None
    preco_total: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo_total: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: Optional[bool] = None
    itens: Optional[List[ComboItemIn]] = Field(default=None, description="Substitui todos os itens do combo")


class ComboItemDTO(BaseModel):
    produto_cod_barras: Optional[str] = None
    receita_id: Optional[int] = None
    quantidade: int

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
    itens: List[ComboItemDTO]
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


from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, constr
from datetime import datetime


class ReceitaIn(BaseModel):
    empresa_id: int
    nome: constr(min_length=1, max_length=100)
    descricao: Optional[str] = None
    preco_venda: Decimal
    imagem: Optional[str] = None
    ativo: bool = True
    disponivel: bool = True


class ReceitaOut(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_venda: Decimal
    custo: Decimal
    imagem: Optional[str] = None
    ativo: bool
    disponivel: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReceitaUpdate(BaseModel):
    nome: Optional[constr(max_length=100)] = None
    descricao: Optional[str] = None
    preco_venda: Optional[Decimal] = None
    imagem: Optional[str] = None
    ativo: Optional[bool] = None
    disponivel: Optional[bool] = None


class ReceitaIngredienteIn(BaseModel):
    """Schema para vincular um ingrediente a uma receita"""
    receita_id: int
    ingrediente_id: int
    quantidade: Optional[float] = None


class ReceitaIngredienteOut(BaseModel):
    """Schema de resposta para ingrediente de receita"""
    id: int
    receita_id: int
    ingrediente_id: int
    quantidade: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


class ReceitaIngredienteDetalhadoOut(BaseModel):
    """Schema de resposta para ingrediente de receita com dados do ingrediente"""
    id: int
    receita_id: int
    ingrediente_id: int
    quantidade: Optional[float] = None
    # Dados do ingrediente
    ingrediente_nome: Optional[str] = None
    ingrediente_descricao: Optional[str] = None
    ingrediente_unidade_medida: Optional[str] = None
    ingrediente_custo: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


class ReceitaComIngredientesOut(BaseModel):
    """Schema de resposta para receita com seus ingredientes incluídos"""
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_venda: Decimal
    custo: Decimal
    imagem: Optional[str] = None
    ativo: bool
    disponivel: bool
    created_at: datetime
    updated_at: datetime
    ingredientes: list[ReceitaIngredienteDetalhadoOut] = []
    model_config = ConfigDict(from_attributes=True)


class AdicionalIn(BaseModel):
    receita_id: int
    adicional_cod_barras: constr(min_length=1)


class AdicionalOut(BaseModel):
    id: int
    receita_id: int
    adicional_cod_barras: str
    preco: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


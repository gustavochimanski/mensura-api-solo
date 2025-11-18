from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, constr, condecimal


# ------ Requests ------
class CriarIngredienteRequest(BaseModel):
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    unidade_medida: Optional[str] = Field(None, max_length=10, description="Unidade de medida (ex: KG, L, UN, GR)")
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0, description="Custo do ingrediente")
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class AtualizarIngredienteRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    unidade_medida: Optional[str] = Field(None, max_length=10)
    custo: Optional[condecimal(max_digits=18, decimal_places=2)] = Field(None, description="Custo do ingrediente")
    ativo: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# ------ Responses ------
class IngredienteResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    unidade_medida: Optional[str] = None
    custo: Decimal
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngredienteResumidoResponse(BaseModel):
    """Versão simplificada para uso em listagens"""
    id: int
    nome: str
    unidade_medida: Optional[str] = None
    custo: Decimal
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


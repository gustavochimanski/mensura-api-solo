from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, constr


# ------ Requests ------
class CriarIngredienteRequest(BaseModel):
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    unidade_medida: Optional[str] = Field(None, max_length=10, description="Unidade de medida (ex: KG, L, UN, GR)")
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class AtualizarIngredienteRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    unidade_medida: Optional[str] = Field(None, max_length=10)
    ativo: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# ------ Responses ------
class IngredienteResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    unidade_medida: Optional[str] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngredienteResumidoResponse(BaseModel):
    """Versão simplificada para uso em listagens"""
    id: int
    nome: str
    unidade_medida: Optional[str] = None
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


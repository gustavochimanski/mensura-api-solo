from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class CaixaBase(BaseModel):
    """Schema base para caixa"""
    nome: str = Field(..., min_length=1, max_length=100, description="Nome/identificação do caixa")
    descricao: Optional[str] = Field(None, max_length=500, description="Descrição opcional do caixa")
    ativo: bool = Field(True, description="Se o caixa está ativo")

class CaixaCreate(CaixaBase):
    """Schema para criar um novo caixa"""
    empresa_id: int = Field(..., gt=0, description="ID da empresa")

class CaixaUpdate(BaseModel):
    """Schema para atualizar um caixa"""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    ativo: Optional[bool] = None

class CaixaResponse(BaseModel):
    """Schema de resposta para caixa"""
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    # Informações adicionais
    empresa_nome: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


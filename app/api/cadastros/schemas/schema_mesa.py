from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from app.api.cadastros.models.model_mesa import StatusMesa


class PedidoAbertoMesa(BaseModel):
    """Schema para pedido aberto em uma mesa."""
    id: int
    numero_pedido: str
    status: str
    num_pessoas: Optional[int] = None
    valor_total: Decimal
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None

    model_config = {"from_attributes": True}


class MesaCreate(BaseModel):
    """Schema para criar uma mesa."""
    codigo: Decimal = Field(..., gt=0, description="Código da mesa (deve ser > 0)")
    descricao: str = Field(..., min_length=1, description="Descrição da mesa")
    capacidade: int = Field(..., gt=0, description="Capacidade máxima (deve ser > 0)")
    status: str = Field(..., description="Status inicial: D=Disponível, O=Ocupada, R=Reservada")
    ativa: str = Field(..., description="S ou N - se a mesa está ativa")
    empresa_id: int = Field(..., gt=0, description="ID da empresa (deve ser > 0)")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ["D", "O", "R"]:
            raise ValueError('Status deve ser "D", "O" ou "R"')
        return v

    @field_validator("ativa")
    @classmethod
    def validate_ativa(cls, v):
        if v not in ["S", "N"]:
            raise ValueError('Ativa deve ser "S" ou "N"')
        return v


class MesaUpdate(BaseModel):
    """Schema para atualizar uma mesa."""
    descricao: Optional[str] = Field(None, min_length=1)
    capacidade: Optional[int] = Field(None, gt=0)
    status: Optional[str] = None
    ativa: Optional[str] = None
    empresa_id: Optional[int] = Field(None, gt=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ["D", "O", "R"]:
            raise ValueError('Status deve ser "D", "O" ou "R"')
        return v

    @field_validator("ativa")
    @classmethod
    def validate_ativa(cls, v):
        if v is not None and v not in ["S", "N"]:
            raise ValueError('Ativa deve ser "S" ou "N"')
        return v


class MesaStatusUpdate(BaseModel):
    """Schema para atualizar apenas o status da mesa."""
    status: str = Field(..., description="D=Disponível, O=Ocupada, R=Reservada")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ["D", "O", "R"]:
            raise ValueError('Status deve ser "D", "O" ou "R"')
        return v


class MesaResponse(BaseModel):
    """Schema de resposta para uma mesa."""
    id: int
    codigo: str  # Convertido para string
    numero: str
    descricao: Optional[str]
    capacidade: int
    status: str
    status_descricao: str
    ativa: str
    label: str
    num_pessoas_atual: Optional[int] = None
    empresa_id: Optional[int] = None
    pedidos_abertos: Optional[List[PedidoAbertoMesa]] = None

    model_config = {"from_attributes": True}


class MesaStatsResponse(BaseModel):
    """Schema para estatísticas de mesas."""
    total: int
    disponiveis: int
    ocupadas: int
    reservadas: int
    inativas: int


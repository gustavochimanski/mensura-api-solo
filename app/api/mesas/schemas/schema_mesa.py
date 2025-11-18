from pydantic import BaseModel, ConfigDict, constr, Field
from typing import Optional, List
from enum import Enum
from decimal import Decimal

from app.api.mesas.models.model_mesa import StatusMesa
from app.api.mesas.schemas.schema_pedido_mesa import StatusPedidoMesaEnum


class StatusMesaEnum(str, Enum):
    """Enum para status de mesa nos schemas"""
    DISPONIVEL = "D"
    OCUPADA = "O"
    RESERVADA = "R"


class MesaIn(BaseModel):
    """Schema para criação de mesa"""
    empresa_id: int = Field(..., description="ID da empresa dona da mesa", gt=0)
    codigo: Decimal = Field(..., description="Código numérico da mesa (número real)", ge=0)
    descricao: Optional[constr(max_length=100)] = None
    capacidade: Optional[int] = Field(default=4, ge=1, le=20)
    status: Optional[StatusMesaEnum] = StatusMesaEnum.DISPONIVEL
    ativa: Optional[constr(pattern="^[SN]$")] = "S"

    model_config = ConfigDict(from_attributes=True)

    def __init__(self, **data):
        # Garante que descricao seja None se for string vazia
        if 'descricao' in data and data['descricao'] == '':
            data['descricao'] = None
        super().__init__(**data)


class MesaOut(BaseModel):
    """Schema para retorno de mesa"""
    id: int
    empresa_id: int
    codigo: Decimal
    numero: str
    descricao: Optional[str] = None
    capacidade: int
    status: StatusMesaEnum
    status_descricao: str
    ativa: str
    label: str
    is_ocupada: bool
    is_disponivel: bool
    is_reservada: bool

    model_config = ConfigDict(from_attributes=True)


class MesaUpdate(BaseModel):
    """Schema para atualização de mesa"""
    empresa_id: Optional[int] = Field(None, description="ID da empresa dona da mesa", gt=0)
    codigo: Optional[Decimal] = Field(None, description="Código numérico da mesa (número real)", ge=0)
    numero: Optional[constr(min_length=1, max_length=10)] = None
    descricao: Optional[constr(max_length=100)] = None
    capacidade: Optional[int] = Field(None, ge=1, le=20)
    status: Optional[StatusMesaEnum] = None
    ativa: Optional[constr(pattern="^[SN]$")] = None

    model_config = ConfigDict(from_attributes=True)

    def __init__(self, **data):
        # Garante que descricao seja None se for string vazia
        if 'descricao' in data and data['descricao'] == '':
            data['descricao'] = None
        super().__init__(**data)


class MesaStatusUpdate(BaseModel):
    """Schema específico para atualização de status"""
    status: StatusMesaEnum

    model_config = ConfigDict(from_attributes=True)


class MesaSearchOut(BaseModel):
    """Schema para busca de mesas"""
    id: int
    empresa_id: int
    codigo: Decimal
    numero: str
    descricao: Optional[str] = None
    capacidade: int
    status: StatusMesaEnum
    status_descricao: str
    ativa: str

    model_config = ConfigDict(from_attributes=True)


class MesaListOut(BaseModel):
    """Schema para listagem de mesas"""
    id: int
    empresa_id: int
    codigo: Decimal
    numero: str
    descricao: Optional[str] = None
    capacidade: int
    status: StatusMesaEnum
    status_descricao: str
    ativa: str
    label: str
    num_pessoas_atual: Optional[int] = None
    cliente_atual_id: Optional[int] = None
    cliente_atual_nome: Optional[str] = None
    pedidos_abertos: List["MesaPedidoResumo"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MesaPedidoResumo(BaseModel):
    id: int
    numero_pedido: str
    status: StatusPedidoMesaEnum
    num_pessoas: Optional[int] = None
    valor_total: float
    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MesaStatsOut(BaseModel):
    """Schema para estatísticas de mesas"""
    total: int
    disponiveis: int
    ocupadas: int
    reservadas: int
    ativas: int
    inativas: int

    model_config = ConfigDict(from_attributes=True)

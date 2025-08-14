from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, constr

class EntregadorCreate(BaseModel):
    nome: constr(min_length=1)
    telefone: Optional[str] = None
    documento: Optional[str] = None  # CPF/CNPJ
    veiculo_tipo: Optional[str] = None  # moto, bike, carro
    placa: Optional[str] = None
    acrescimo_taxa: Optional[float] = 0.0

class EntregadorUpdate(BaseModel):
    nome: Optional[constr(min_length=1)] = None
    telefone: Optional[str] = None
    documento: Optional[str] = None
    veiculo_tipo: Optional[str] = None
    placa: Optional[str] = None
    acrescimo_taxa: Optional[float] = None

class EntregadorOut(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    documento: Optional[str]
    veiculo_tipo: Optional[str]
    placa: Optional[str]
    acrescimo_taxa: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

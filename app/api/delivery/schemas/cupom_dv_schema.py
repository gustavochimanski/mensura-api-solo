from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, constr

class CupomCreate(BaseModel):
    codigo: constr(min_length=1, max_length=30)
    descricao: Optional[constr(max_length=120)] = None
    desconto_valor: Optional[float] = None
    desconto_percentual: Optional[float] = None  # 0-100
    ativo: bool = True
    validade_inicio: Optional[datetime] = None
    validade_fim: Optional[datetime] = None
    minimo_compra: Optional[float] = None

class CupomUpdate(BaseModel):
    descricao: Optional[constr(max_length=120)] = None
    desconto_valor: Optional[float] = None
    desconto_percentual: Optional[float] = None
    ativo: Optional[bool] = None
    validade_inicio: Optional[datetime] = None
    validade_fim: Optional[datetime] = None
    minimo_compra: Optional[float] = None

class CupomOut(BaseModel):
    id: int
    codigo: str
    descricao: Optional[str]
    desconto_valor: Optional[float]
    desconto_percentual: Optional[float]
    ativo: bool
    validade_inicio: Optional[datetime]
    validade_fim: Optional[datetime]
    minimo_compra: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

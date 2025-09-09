from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, constr, ConfigDict

class CupomCreate(BaseModel):
    codigo: constr(min_length=1, max_length=30)
    descricao: Optional[constr(max_length=120)] = None
    desconto_valor: Optional[float] = None
    desconto_percentual: Optional[float] = None
    ativo: bool = True
    validade_inicio: Optional[datetime] = None
    validade_fim: Optional[datetime] = None

    monetizado: bool = False
    valor_por_lead: Optional[float] = None
    parceiro_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class CupomUpdate(BaseModel):
    descricao: Optional[constr(max_length=120)] = None
    desconto_valor: Optional[float] = None
    desconto_percentual: Optional[float] = None
    ativo: Optional[bool] = None
    validade_inicio: Optional[datetime] = None
    validade_fim: Optional[datetime] = None

    monetizado: Optional[bool] = None
    valor_por_lead: Optional[float] = None
    parceiro_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class CupomOut(BaseModel):
    id: int
    codigo: str
    descricao: Optional[str]
    desconto_valor: Optional[float]
    desconto_percentual: Optional[float]
    ativo: bool
    validade_inicio: Optional[datetime]
    validade_fim: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    monetizado: bool
    valor_por_lead: Optional[float]
    link_whatsapp: Optional[str]

    model_config = ConfigDict(from_attributes=True)

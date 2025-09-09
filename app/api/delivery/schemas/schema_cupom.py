from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, constr, ConfigDict

# ------------------- CUPOM -------------------
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


# ------------------- LINK -------------------
class CupomLinkCreate(BaseModel):
    titulo: constr(min_length=1, max_length=100)
    url: constr(min_length=1, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class CupomLinkOut(BaseModel):
    id: int
    cupom_id: int
    titulo: str
    url: str

    model_config = ConfigDict(from_attributes=True)


# ------------------- CUPOM COM LINKS -------------------
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

    # ✅ Lista de links do cupom
    links: List[CupomLinkOut] = []

    model_config = ConfigDict(from_attributes=True)

class CupomParceiroOut(BaseModel):
    id: int
    codigo: str
    descricao: Optional[str]
    desconto_valor: Optional[float]
    desconto_percentual: Optional[float]
    ativo: bool
    monetizado: bool
    valor_por_lead: Optional[float]
    links: List[CupomLinkOut] = []

    model_config = ConfigDict(from_attributes=True)
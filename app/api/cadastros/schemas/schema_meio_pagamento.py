from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum

class MeioPagamentoTipoEnum(str, Enum):
    CARTAO_ENTREGA = "CARTAO_ENTREGA"
    PIX_ENTREGA = "PIX_ENTREGA"
    DINHEIRO = "DINHEIRO"
    PIX_ONLINE = "PIX_ONLINE"
    OUTROS = "OUTROS"

class MeioPagamentoBase(BaseModel):
    nome: str
    tipo: MeioPagamentoTipoEnum
    ativo: bool = True

class MeioPagamentoCreate(MeioPagamentoBase):
    pass

class MeioPagamentoUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[MeioPagamentoTipoEnum] = None
    ativo: Optional[bool] = None

class MeioPagamentoResponse(MeioPagamentoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


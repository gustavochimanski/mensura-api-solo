from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, constr, ConfigDict

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

    # ✅ Substituímos o link único por uma lista de links
    links: List["CupomLinkOut"] = []

    model_config = ConfigDict(from_attributes=True)


# ------------------- Links -------------------
class CupomLinkOut(BaseModel):
    id: int
    cupom_id: int
    titulo: str
    url: str

    model_config = ConfigDict(from_attributes=True)

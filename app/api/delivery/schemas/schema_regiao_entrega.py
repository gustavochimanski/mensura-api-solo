from pydantic import BaseModel, Field
from typing import Optional

class RegiaoEntregaBase(BaseModel):
    cep: Optional[str] = Field(None, example="01001-000")
    bairro: str
    cidade: str
    uf: str
    taxa_entrega: float
    ativo: bool = True

class RegiaoEntregaCreate(RegiaoEntregaBase):
    empresa_id: int

class RegiaoEntregaUpdate(RegiaoEntregaBase):
    pass

class RegiaoEntregaOut(RegiaoEntregaBase):
    id: int
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True

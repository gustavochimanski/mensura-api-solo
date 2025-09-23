from pydantic import BaseModel, Field, condecimal
from typing import Optional

#
class RegiaoEntregaBase(BaseModel):
    cep: Optional[str] = Field(None, example="01001-000")
    bairro: str = Field(..., example="Centro")
    cidade: str = Field(..., example="São Paulo")
    uf: str = Field(..., min_length=2, max_length=2, example="SP")
    taxa_entrega: condecimal(gt=0, decimal_places=2) = Field(..., example=8.90)
    ativo: bool = True


class RegiaoEntregaCreate(RegiaoEntregaBase):
    empresa_id: int = Field(..., example=1)


class RegiaoEntregaUpdate(RegiaoEntregaBase):
    pass


class RegiaoEntregaOut(RegiaoEntregaBase):
    id: int

    class Config:
        from_attributes = True

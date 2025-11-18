from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, condecimal


class RegiaoEntregaBase(BaseModel):
    distancia_max_km: condecimal(gt=0, decimal_places=2) = Field(
        ...,
        example="5.00",
        description="Distância em quilômetros atendida por esta faixa.",
    )
    taxa_entrega: condecimal(ge=0, decimal_places=2) = Field(..., example="8.90")
    tempo_estimado_min: Optional[int] = Field(
        None,
        ge=0,
        example=30,
        description="Tempo estimado de entrega, em minutos, para esta quilometragem.",
    )


class RegiaoEntregaCreate(RegiaoEntregaBase):
    empresa_id: int = Field(..., example=1)


class RegiaoEntregaUpdate(RegiaoEntregaBase):
    pass


class RegiaoEntregaOut(RegiaoEntregaBase):
    id: int

    class Config:
        from_attributes = True

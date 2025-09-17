from pydantic import BaseModel, Field, condecimal
from typing import Optional

#
class RegiaoEntregaBase(BaseModel):
    cep: Optional[str] = Field(None, example="01001-000")
    bairro: str = Field(..., example="Centro")
    cidade: str = Field(..., example="São Paulo")
    uf: str = Field(..., min_length=2, max_length=2, example="SP")
    taxa_entrega: condecimal(gt=0, decimal_places=2) = Field(..., example=8.90)
    raio_km: Optional[condecimal(gt=0, decimal_places=2)] = Field(None, example=2.0, description="Raio de cobertura em km")
    ativo: bool = True
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class RegiaoEntregaCreate(RegiaoEntregaBase):
    empresa_id: int = Field(..., example=1)


class RegiaoEntregaUpdate(RegiaoEntregaBase):
    pass


class RegiaoEntregaOut(RegiaoEntregaBase):
    id: int

    class Config:
        from_attributes = True

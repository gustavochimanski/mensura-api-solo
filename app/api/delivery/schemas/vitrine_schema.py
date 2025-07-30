# app/api/mensura/schemas/delivery/vitrines/vitrine_dv_schema.py
from pydantic import BaseModel, ConfigDict

class CriarVitrineRequest(BaseModel):
    cod_categoria: int
    titulo: str
    ordem: int

    model_config = ConfigDict(from_attributes=True)

class CriarVitrineResponse(BaseModel):
    id: int
    cod_categoria: int
    titulo: str
    slug: str
    ordem: int

    model_config = ConfigDict(from_attributes=True)

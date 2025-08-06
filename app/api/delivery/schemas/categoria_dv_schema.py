# app/api/delivery/schemas/categoria_dv_schema.py
from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CategoriaDeliveryIn(BaseModel):
    descricao: constr(min_length=1, max_length=100)
    slug: constr(min_length=1, max_length=100)
    parent_id: Optional[int] = None
    imagem: Optional[str] = None
    posicao: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class CategoriaDeliveryOut(BaseModel):
    id: int
    label: str
    slug: str
    parent_id: Optional[int] = None
    imagem: Optional[str] = None
    href: str
    posicao: int

    model_config = ConfigDict(from_attributes=True)

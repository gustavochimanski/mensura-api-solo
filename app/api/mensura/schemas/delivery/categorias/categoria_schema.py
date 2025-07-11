# app/api/mensura/schemas/delivery/categorias/categoria_schema.py
from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CategoriaDeliveryIn(BaseModel):
    descricao: constr(min_length=1, max_length=100)
    slug: constr(min_length=1, max_length=100)
    slug_pai: Optional[str] = None
    imagem: Optional[str] = None
    posicao: Optional[int] = None   # ⬅️ incluído

    model_config = ConfigDict(from_attributes=True)

class CategoriaDeliveryOut(BaseModel):
    id: int
    label: str
    imagem: Optional[str]
    slug: str
    slug_pai: Optional[str]
    href: str
    posicao: Optional[int]           # ⬅️ incluído

    model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CategoriaDeliveryIn(BaseModel):
    descricao: constr(min_length=1, max_length=100)
    slug: constr(min_length=1, max_length=100)
    parent_id: Optional[int] = None
    imagem: Optional[str] = None
    posicao: Optional[int] = 0
    # controla presença na home
    tipo_exibicao: Optional[constr(min_length=1, max_length=1)] = None  # "P" = aparece na home

    model_config = ConfigDict(from_attributes=True)

class CategoriaDeliveryOut(BaseModel):
    id: int
    label: str
    slug: str
    parent_id: Optional[int] = None
    slug_pai: Optional[str] = None
    imagem: Optional[str] = None
    href: str
    posicao: int
    is_home: bool  # property derivada

    model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CategoriaDeliveryIn(BaseModel):
    descricao: constr(min_length=1, max_length=100)
    slug: constr(min_length=1, max_length=100)
    parent_id: Optional[int] = None
    imagem: Optional[str] = None
    posicao: Optional[int] = 0

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

    model_config = ConfigDict(from_attributes=True)


class CategoriaSearchOut(BaseModel):
    id: int
    descricao: str
    slug: str
    parent_id: Optional[int] = None
    slug_pai: Optional[str] = None
    imagem: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoriaFlatOut(BaseModel):
    id: int
    slug: str
    parent_id: Optional[int] = None
    descricao: str
    posicao: int
    imagem: Optional[str] = None
    label: str
    href: str
    slug_pai: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
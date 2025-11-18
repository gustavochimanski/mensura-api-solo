from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CategoriaDeliveryIn(BaseModel):
    descricao: constr(min_length=1, max_length=100)
    slug: Optional[str] = None  # Slug será gerado automaticamente se não fornecido
    parent_id: Optional[int] = None
    imagem: Optional[str] = None
    posicao: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
    
    def __init__(self, **data):
        # Garante que imagem seja None se for string vazia
        if 'imagem' in data and data['imagem'] == '':
            data['imagem'] = None
        # Garante que slug seja None se for string vazia
        if 'slug' in data and data['slug'] == '':
            data['slug'] = None
        super().__init__(**data)

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


class CategoriaDeliveryAdminIn(CategoriaDeliveryIn):
    cod_empresa: int


class CategoriaDeliveryAdminUpdate(BaseModel):
    descricao: Optional[str] = None
    parent_id: Optional[int] = None
    imagem: Optional[str] = None
    posicao: Optional[int] = None
    cod_empresa: int

    model_config = ConfigDict(extra="forbid")


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

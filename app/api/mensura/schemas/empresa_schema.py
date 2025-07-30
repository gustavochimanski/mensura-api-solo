from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.api.mensura.schemas.endereco_schema import EnderecoCreate


class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None
    endereco: EnderecoCreate

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    logo: Optional[str] = None
    endereco: EnderecoCreate

class EmpresaResponse(EmpresaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

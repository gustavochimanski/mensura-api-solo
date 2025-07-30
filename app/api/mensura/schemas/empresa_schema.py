# empresa_schema.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.api.mensura.schemas.endereco_schema import EnderecoCreate, EnderecoResponse

class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    endereco: EnderecoCreate

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    logo: Optional[str] = None
    endereco_id: Optional[int] = None  # ou endereco: EnderecoUpdate se quiser editar inline

class EmpresaResponse(EmpresaBase):
    id: int
    endereco: Optional[EnderecoResponse] = None

    model_config = ConfigDict(from_attributes=True)

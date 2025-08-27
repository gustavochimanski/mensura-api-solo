from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.api.mensura.schemas.endereco_schema import EnderecoCreate, EnderecoResponse

class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None  # URL da logo no banco

class EmpresaCreate(EmpresaBase):
    endereco: EnderecoCreate  # JSON do endereço

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    endereco_id: Optional[int] = None

class EmpresaResponse(EmpresaBase):
    id: int
    endereco: Optional[EnderecoResponse] = None
    model_config = ConfigDict(from_attributes=True)

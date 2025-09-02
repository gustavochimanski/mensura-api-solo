# app/api/mensura/schemas/empresa_schema.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.api.mensura.schemas.schema_endereco import EnderecoResponse, EnderecoCreate


class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None
    # Configurações do Cardápio
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = "padrao"

class EmpresaCreate(EmpresaBase):
    endereco: EnderecoCreate  # JSON do endereço

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    endereco_id: Optional[int] = None
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None

class EmpresaResponse(EmpresaBase):
    id: int
    endereco: Optional[EnderecoResponse] = None
    model_config = ConfigDict(from_attributes=True)

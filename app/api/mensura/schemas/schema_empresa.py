# app/api/mensura/schemas/schema_empresa.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from app.api.mensura.schemas.schema_endereco import EnderecoResponse, EnderecoCreate

class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = "padrao"
    aceita_pedido_automatico: bool = False
    tempo_entrega_maximo: int = Field(..., gt=0)

class EmpresaCreate(EmpresaBase):
    endereco: EnderecoCreate  # obrigatório na criação

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    endereco_id: Optional[int] = None  # para atualizar endereço existente
    aceita_pedido_automatico: Optional[bool] = None
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None
    endereco: Optional[EnderecoCreate] = None  # novo objeto para atualizar
    tempo_entrega_maximo: Optional[int] = Field(None, gt=0)

class EmpresaResponse(EmpresaBase):
    id: int
    endereco_id: Optional[int] = None
    endereco: Optional[EnderecoResponse] = None

    model_config = ConfigDict(from_attributes=True)


class EmpresaCardapioLinkResponse(BaseModel):
    id: int
    nome: str
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
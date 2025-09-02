# app/api/mensura/schemas/empresa_schema.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.api.mensura.schemas.schema_endereco import EnderecoResponse, EnderecoCreate


class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None
    aceita_pedido_automatico: Optional[bool] = False  # <--- novo campo
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = "padrao"


class EmpresaCreate(EmpresaBase):
    endereco: EnderecoCreate


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    endereco_id: Optional[int] = None
    aceita_pedido_automatico: Optional[bool] = None  # <--- novo campo
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None


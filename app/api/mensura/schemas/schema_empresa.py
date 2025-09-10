# app/api/mensura/schemas/empresa_schema.py
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
    taxa_minima_entrega: float = Field(..., ge=0)


class EmpresaCreate(EmpresaBase):
    endereco: EnderecoCreate


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    endereco_id: Optional[int] = None
    aceita_pedido_automatico: Optional[bool] = None
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None
    tempo_entrega_maximo: int | None = Field(None, gt=0)
    taxa_minima_entrega: float | None = Field(None, ge=0)


class EmpresaResponse(EmpresaBase):
    id: int
    endereco: Optional[EnderecoResponse] = None
    model_config = ConfigDict(from_attributes=True)

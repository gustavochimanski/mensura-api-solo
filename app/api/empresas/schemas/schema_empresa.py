# app/api/empresas/schemas/schema_empresa.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = "padrao"
    aceita_pedido_automatico: bool = False
    tempo_entrega_maximo: int = Field(..., gt=0)

    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    ponto_referencia: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    slug: Optional[str] = None
    aceita_pedido_automatico: Optional[bool] = None
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None
    tempo_entrega_maximo: Optional[int] = Field(None, gt=0)

    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    ponto_referencia: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class EmpresaResponse(EmpresaBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class EmpresaCardapioLinkResponse(BaseModel):
    id: int
    nome: str
    cardapio_link: Optional[str] = None
    cardapio_tema: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


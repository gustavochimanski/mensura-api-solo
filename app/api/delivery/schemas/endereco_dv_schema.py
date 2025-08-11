from pydantic import BaseModel, ConfigDict
from typing import Optional

class EnderecoBase(BaseModel):
    cliente_id: int
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None

    # extras do model
    ponto_referencia: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_principal: bool = False

class EnderecoCreate(EnderecoBase):
    pass

class EnderecoUpdate(BaseModel):
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
    is_principal: Optional[bool] = None

class EnderecoResponse(EnderecoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

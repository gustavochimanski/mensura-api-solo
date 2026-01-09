from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional

class EnderecoBase(BaseModel):
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

    @field_validator('estado', mode='before')
    @classmethod
    def validar_estado(cls, v):
        if v is None or v == "":
            return v
        # Limita a 2 caracteres e converte para maiúsculo
        return str(v)[:2].upper()

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

    @field_validator('estado', mode='before')
    @classmethod
    def validar_estado(cls, v):
        if v is None or v == "":
            return v
        # Limita a 2 caracteres e converte para maiúsculo
        return str(v)[:2].upper()

class EnderecoOut(EnderecoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

# Alias para compatibilidade
EnderecoResponse = EnderecoOut

# app/api/mensura/schemas/schema_endereco.py
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
    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: Optional[str]):
        if v and len(v) != 2:
            raise ValueError("Estado deve ter exatamente 2 caracteres (ex: 'SP')")
        return v.upper() if v else v

class EnderecoCreate(EnderecoBase):
    pass

class EnderecoUpdate(EnderecoBase):
    pass

class EnderecoResponse(EnderecoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

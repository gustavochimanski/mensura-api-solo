from pydantic import BaseModel, ConfigDict
from typing import Optional

class EnderecoBase(BaseModel):
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None

class EnderecoCreate(EnderecoBase):
    pass

class EnderecoUpdate(EnderecoBase):
    pass

class EnderecoResponse(EnderecoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

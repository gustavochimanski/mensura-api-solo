# app/api/mensura/schemas/cliente_schema.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date

class ClienteBase(BaseModel):
    nome: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class ClienteResponse(ClienteBase):
    id: int

    class Config:
        orm_mode = True

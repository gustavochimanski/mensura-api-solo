# src/app/api/delivery/schemas/cliente_schemas.py
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, constr, ConfigDict

# Resposta para o cliente
class ClienteOut(BaseModel):
    id: int
    nome: str
    cpf: Optional[str]
    telefone: str
    email: Optional[EmailStr]
    data_nascimento: Optional[date]
    ativo: bool

    model_config = ConfigDict(from_attributes=True)

# Campos para criação
class ClienteCreate(BaseModel):
    nome: constr(min_length=1, max_length=100)
    cpf: Optional[constr(max_length=14)] = None
    telefone: Optional[constr(max_length=20)] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None

# Campos para atualização parcial
class ClienteUpdate(BaseModel):
    nome: Optional[constr(min_length=1, max_length=100)] = None
    cpf: Optional[constr(max_length=14)] = None
    telefone: Optional[constr(max_length=20)] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = None

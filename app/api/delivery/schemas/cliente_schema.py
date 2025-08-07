# src/app/api/delivery/schemas/cliente_schemas.py
from datetime import date
from pydantic import BaseModel, EmailStr, constr, ConfigDict


# Campos que vêm na resposta
class ClienteOut(BaseModel):
    id: int
    nome: constr(min_length=1, max_length=100)
    cpf: constr(max_length=14) | None
    telefone: constr(max_length=20) | None
    email: EmailStr | None
    data_nascimento: date | None
    ativo: bool

    model_config = ConfigDict(from_attributes=True)

# Campos para criação
class ClienteCreate(BaseModel):
    nome: constr(min_length=1, max_length=100)
    cpf: constr(max_length=14) | None = None
    telefone: constr(max_length=20) | None = None
    email: EmailStr | None = None
    data_nascimento: date | None = None

# Campos para atualização parcial
class ClienteUpdate(BaseModel):
    nome: constr(min_length=1, max_length=100) | None = None
    cpf: constr(max_length=14) | None = None
    telefone: constr(max_length=20) | None = None
    email: EmailStr | None = None
    data_nascimento: date | None = None
    ativo: bool | None = None

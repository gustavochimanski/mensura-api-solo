from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, constr, ConfigDict

class ClienteOut(BaseModel):
    id: int
    nome: str
    cpf: Optional[str]
    telefone: Optional[str]
    email: Optional[EmailStr]
    data_nascimento: Optional[date]
    ativo: bool
    super_token: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClienteCreate(BaseModel):
    nome: str
    cpf: Optional[constr(max_length=14)] = None
    telefone: str
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None

class ClienteUpdate(BaseModel):
    nome: Optional[constr(min_length=1, max_length=100)] = None
    cpf: Optional[constr(max_length=14)] = None
    telefone: Optional[constr(max_length=20)] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = None


from pydantic import BaseModel, constr

class NovoDispositivoRequest(BaseModel):
    telefone: constr(min_length=10, max_length=11)

class ConfirmacaoCodigoRequest(BaseModel):
    telefone: constr(min_length=10, max_length=11)
    codigo: str

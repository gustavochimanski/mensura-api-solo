from datetime import date, datetime
from typing import Optional, List, Literal, Union
from pydantic import BaseModel, EmailStr, constr, ConfigDict, field_validator, model_validator

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
    email: Optional[str] = None
    data_nascimento: Optional[Union[str, date]] = None

    @model_validator(mode='before')
    @classmethod
    def normalize_empty_strings(cls, data):
        """Converte strings vazias para None em campos opcionais."""
        if isinstance(data, dict):
            # Normaliza CPF - converte representações vazias para None
            if 'cpf' in data:
                cpf_value = data['cpf']
                if isinstance(cpf_value, str):
                    sanitized = cpf_value.strip()
                    if sanitized == "" or sanitized.lower() in {"null", "none", "undefined"}:
                        data['cpf'] = None
                    else:
                        data['cpf'] = sanitized
                elif cpf_value is None:
                    data['cpf'] = None

            # Normaliza email - converte string vazia para None
            if 'email' in data:
                if data['email'] == "" or (isinstance(data['email'], str) and data['email'].strip() == ""):
                    data['email'] = None
                elif isinstance(data['email'], str):
                    data['email'] = data['email'].strip() or None
            
            # Normaliza data_nascimento - converte string vazia para None
            if 'data_nascimento' in data:
                if data['data_nascimento'] == "" or (isinstance(data['data_nascimento'], str) and data['data_nascimento'].strip() == ""):
                    data['data_nascimento'] = None
                elif isinstance(data['data_nascimento'], str) and data['data_nascimento'].strip():
                    # Tenta converter string para date
                    try:
                        date_str = data['data_nascimento'].strip()
                        if len(date_str) == 10:
                            data['data_nascimento'] = datetime.strptime(date_str, "%Y-%m-%d").date()
                        else:
                            data['data_nascimento'] = None
                    except (ValueError, TypeError):
                        data['data_nascimento'] = None
        return data

class ClienteUpdate(BaseModel):
    nome: Optional[constr(min_length=1, max_length=100)] = None
    cpf: Optional[constr(max_length=14)] = None
    telefone: Optional[constr(max_length=20)] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = None

    @field_validator('cpf', mode='before')
    @classmethod
    def validate_cpf(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            sanitized = v.strip()
            if sanitized == "" or sanitized.lower() in {"null", "none", "undefined"}:
                return None
            return sanitized
        return v

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v == "" or v is None:
            return None
        return v

    @field_validator('data_nascimento', mode='before')
    @classmethod
    def validate_data_nascimento(cls, v):
        if v == "" or v is None:
            return None
        return v

class EnderecoUpdateAdmin(BaseModel):
    acao: Literal["add", "update", "remove"]  # Ação a ser executada
    id: Optional[int] = None  # Para identificar endereço existente (obrigatório para update/remove)
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

class ClienteAdminUpdate(BaseModel):
    nome: Optional[constr(min_length=1, max_length=100)] = None
    cpf: Optional[constr(max_length=14)] = None
    telefone: Optional[constr(max_length=20)] = None
    email: Optional[EmailStr] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = None
    endereco: Optional[EnderecoUpdateAdmin] = None

    @field_validator('cpf', mode='before')
    @classmethod
    def validate_cpf(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            sanitized = v.strip()
            if sanitized == "" or sanitized.lower() in {"null", "none", "undefined"}:
                return None
            return sanitized
        return v

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v == "" or v is None:
            return None
        return v

    @field_validator('data_nascimento', mode='before')
    @classmethod
    def validate_data_nascimento(cls, v):
        if v == "" or v is None:
            return None
        return v


from pydantic import BaseModel, constr

class NovoDispositivoRequest(BaseModel):
    telefone: constr(min_length=10, max_length=11)


# app/api/empresas/schemas/schema_empresa.py
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List


class HorarioIntervalo(BaseModel):
    inicio: str = Field(..., description="Hora inicial no formato HH:MM")
    fim: str = Field(..., description="Hora final no formato HH:MM")

    @field_validator("inicio", "fim")
    @classmethod
    def _validar_hhmm(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Hora deve ser string no formato HH:MM")
        v = v.strip()
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Hora deve estar no formato HH:MM")
        hh, mm = v.split(":")
        h, m = int(hh), int(mm)
        if h < 0 or h > 23 or m < 0 or m > 59:
            raise ValueError("Hora inválida (use 00:00 até 23:59)")
        return v


class HorarioDia(BaseModel):
    dia_semana: int = Field(..., ge=0, le=6, description="0=domingo, 1=segunda, ..., 6=sábado")
    intervalos: List[HorarioIntervalo] = Field(default_factory=list)

class EmpresaBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    slug: str
    logo: Optional[str] = None
    timezone: Optional[str] = "America/Sao_Paulo"
    horarios_funcionamento: Optional[List[HorarioDia]] = None
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
    timezone: Optional[str] = None
    horarios_funcionamento: Optional[List[HorarioDia]] = None
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


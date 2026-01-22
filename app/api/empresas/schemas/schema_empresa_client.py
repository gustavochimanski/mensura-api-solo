# app/api/empresas/schemas/schema_empresa_client.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any


class HorarioIntervaloOut(BaseModel):
    inicio: str
    fim: str


class HorarioDiaOut(BaseModel):
    dia_semana: int
    intervalos: List[HorarioIntervaloOut] = Field(default_factory=list)


class EmpresaClientOut(BaseModel):
    nome: str
    logo: Optional[str] = None
    timezone: Optional[str] = None
    horarios_funcionamento: Optional[List[HorarioDiaOut]] = None
    cardapio_tema: Optional[str] = "padrao"
    aceita_pedido_automatico: bool = False
    tempo_entrega_maximo: int = Field(..., gt=0)
    redireciona_home: bool = False
    redireciona_home_para: Optional[str] = None
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

    model_config = ConfigDict(from_attributes=True)


class EmpresaPublicListItem(BaseModel):
    id: int
    nome: str
    logo: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    distancia_km: Optional[float] = None
    tema: Optional[str] = None
    redireciona_home: bool = False
    redireciona_home_para: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


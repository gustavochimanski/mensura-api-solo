from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, constr

class EntregadorCreate(BaseModel):
    nome: constr(min_length=1)
    telefone: Optional[str] = None
    documento: Optional[str] = None  # CPF/CNPJ
    veiculo_tipo: Optional[str] = None  # moto, bike, carro
    placa: Optional[str] = None
    acrescimo_taxa: Optional[float] = 0.0
    valor_diaria: Optional[float] = None
    empresa_id: int

class EntregadorUpdate(BaseModel):
    nome: Optional[constr(min_length=1)] = None
    telefone: Optional[str] = None
    documento: Optional[str] = None
    veiculo_tipo: Optional[str] = None
    placa: Optional[str] = None
    acrescimo_taxa: Optional[float] = None
    valor_diaria: Optional[float] = None

class EmpresaMiniOut(BaseModel):
    id: int
    nome: str

    model_config = ConfigDict(from_attributes=True)

class EntregadorOut(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    documento: Optional[str]
    veiculo_tipo: Optional[str]
    placa: Optional[str]
    acrescimo_taxa: Optional[float]
    valor_diaria: Optional[float]
    created_at: datetime
    updated_at: datetime
    empresas: List[EmpresaMiniOut] = []

    model_config = ConfigDict(from_attributes=True)


class EntregadorRelatorioDiaOut(BaseModel):
    data: date
    qtd_pedidos: int
    valor_total: float


class EntregadorRelatorioDiaAcertoOut(BaseModel):
    data: date
    qtd_pedidos_acertados: int
    valor_total_acertado: float


class EntregadorRelatorioEmpresaOut(BaseModel):
    empresa_id: int
    empresa_nome: Optional[str] = None

    total_pedidos: int
    total_pedidos_entregues: int
    total_pedidos_cancelados: int
    total_pedidos_pagos: int

    valor_total: float
    ticket_medio: float
    ticket_medio_entregues: float

    tempo_medio_entrega_minutos: float

    dias_ativos: int
    pedidos_medio_por_dia: float
    valor_medio_por_dia: float

    total_pedidos_acertados: int
    total_valor_acertado: float
    media_pedidos_acertados_por_dia: float
    media_valor_acertado_por_dia: float

    total_pedidos_pendentes_acerto: int
    total_valor_pendente_acerto: float


class EntregadorRelatorioDetalhadoOut(BaseModel):
    entregador_id: int
    entregador_nome: Optional[str] = None
    empresa_id: Optional[int] = None
    inicio: datetime
    fim: datetime

    total_pedidos: int
    total_pedidos_entregues: int
    total_pedidos_cancelados: int
    total_pedidos_pagos: int

    valor_total: float
    ticket_medio: float
    ticket_medio_entregues: float

    tempo_medio_entrega_minutos: float

    dias_no_periodo: int
    dias_ativos: int
    pedidos_medio_por_dia: float
    valor_medio_por_dia: float

    total_pedidos_acertados: int
    total_valor_acertado: float
    media_pedidos_acertados_por_dia: float
    media_valor_acertado_por_dia: float

    total_pedidos_pendentes_acerto: int
    total_valor_pendente_acerto: float

    resumo_por_dia: List[EntregadorRelatorioDiaOut] = []
    resumo_acertos_por_dia: List[EntregadorRelatorioDiaAcertoOut] = []

    empresas: List[EntregadorRelatorioEmpresaOut] = []


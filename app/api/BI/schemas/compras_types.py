# app/schemas/compras_types.py
from datetime import date
from pydantic import BaseModel
from typing import List

class ConsultaMovimentoCompraRequest(BaseModel):
    empresas: List[str]
    dataInicio: str   # "YYYY-MM-DD"
    dataFinal: str

class ConsultaMovimentoTotalEmpresa(BaseModel):
    empresa: str
    valorTotal: float

class ConsultaMovimentoCompraResponse(BaseModel):
    por_empresa: List[ConsultaMovimentoTotalEmpresa]
    total_geral: float

class CompraDetalhadaByDate(BaseModel):
    data: date
    valor: float

class CompraDetalhadaEmpresas(BaseModel):
    empresa: str
    dates: List[CompraDetalhadaByDate]

class CompraDetalhadaResponse(BaseModel):
    empresas: List[str]
    dataInicio: date
    dataFinal: date
    compraEmpresas: List[CompraDetalhadaEmpresas]

# app/schemas/vendaDetalhadaTypes.py
from pydantic import BaseModel
from typing import List, Optional

class TypeVendaPorHora(BaseModel):
    hora: int
    total_cupons: int
    total_vendas: float
    ticket_medio: float

class TypeVendaPorHoraResponse(BaseModel):
    empresa: str
    vendasPorHora: List[TypeVendaPorHora]

# Novo schema para o retorno completo, com totalGeral
class TypeVendaPorHoraComTotalGeralResponse(BaseModel):
    totalGeral: List[TypeVendaPorHora]
    porEmpresa: List[TypeVendaPorHoraResponse]

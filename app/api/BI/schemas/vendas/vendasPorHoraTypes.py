from pydantic import BaseModel
from typing import List

class TypeVendaPorHora(BaseModel):
    hora: int
    total_cupons: int
    total_vendas: float
    ticket_medio: float

class TypeVendaPorHoraResponse(BaseModel):
    empresa: str
    vendasPorHora: List[TypeVendaPorHora]

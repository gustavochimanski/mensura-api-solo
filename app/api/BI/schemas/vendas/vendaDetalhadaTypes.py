from typing import List
from pydantic import BaseModel

class TypeVendaByDay(BaseModel):
    data: str
    valor: float

class TypeVendaDetalhadaEmpresa(BaseModel):
    empresa: str
    dates: List[TypeVendaByDay]

class TypeVendaDetalhadaResponse(BaseModel):
    dataInicio: str
    dataFinal: str
    vendaEmpresas: List[TypeVendaDetalhadaEmpresa]

from typing import List
from pydantic import BaseModel

class TypeVendaByDay(BaseModel):
    data: str
    valor: float

class TypeVendaDetalhadaEmpresa(BaseModel):
    empresa: str
    dates: List[TypeVendaByDay]

class TypeVendaDetalhadaRequest(BaseModel):
    empresas: List[str]
    dataInicio: str
    dataFinal: str

class TypeVendaDetalhadaResponse(BaseModel):
    dataInicio: str
    dataFinal: str
    vendaEmpresas: List[TypeVendaDetalhadaEmpresa]

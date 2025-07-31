from pydantic import BaseModel
from typing import List


class MeioPagamentoResumoResponse(BaseModel):
    tipo: str
    descricao: str
    valor_total: float


class MeioPagamentoPorEmpresa(BaseModel):
    empresa: str
    meios: List[MeioPagamentoResumoResponse]


class MeioPagamentoResponseFinal(BaseModel):
    total_geral: List[MeioPagamentoResumoResponse]
    por_empresa: List[MeioPagamentoPorEmpresa]

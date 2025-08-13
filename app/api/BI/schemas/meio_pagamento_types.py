# app/api/BI/schemas/meio_pagamento_types.py
from pydantic import BaseModel
from typing import List

class MeioPagamentoResumoResponse(BaseModel):
    tipo: str
    descricao: str
    valor_total: float
    retiradas: float = 0.0   # 👈 novo
    qtde: int = 0            # 👈 novo

class MeioPagamentoPorEmpresa(BaseModel):
    empresa: str
    meios: List[MeioPagamentoResumoResponse]

class MeioPagamentoResponseFinal(BaseModel):
    total_geral: List[MeioPagamentoResumoResponse]
    por_empresa: List[MeioPagamentoPorEmpresa]

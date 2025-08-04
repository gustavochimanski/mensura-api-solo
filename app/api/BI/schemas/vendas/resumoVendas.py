# ----------------- schemas.py -----------------
from pydantic import BaseModel
from typing import Optional, List

class TotaisPorEmpresa(BaseModel):
    lcpr_codempresa: str
    empr_nomereduzido: Optional[str]
    total_cupons: int
    total_vendas: float
    ticket_medio: float

class TotaisGerais(BaseModel):
    total_cupons: int
    total_vendas: float
    ticket_medio: float

class ResumoVendasComparativo(BaseModel):
    atual: List[TotaisPorEmpresa]
    anterior: List[TotaisPorEmpresa]

class TypeResumoVendasResponse(BaseModel):
    totais_por_empresa: List[TotaisPorEmpresa]
    total_geral: TotaisGerais
    resumo_venda_compara_periodo: ResumoVendasComparativo
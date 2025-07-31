# ----------------- schemas.py -----------------
from pydantic import BaseModel
from typing import Optional, List

class TypeVendasPeriodoGeral(BaseModel):
    empresas: List[str]
    dataInicio: str  # ISO ‘YYYY‑MM‑DD’
    dataFinal: str
    situacao: Optional[str] = None
    status_venda: Optional[str] = None
    cod_vendedor: Optional[str] = None      # mantive, você já usa

class TotaisPorEmpresa(BaseModel):
    lcpr_codempresa: str
    lcpr_nomereduzido: str
    total_cupons: int
    total_vendas: float
    ticket_medio: float

class TotaisGerais(BaseModel):
    total_cupons: int
    total_vendas: float
    ticket_medio: float

class TypeResumoVendasResponse(BaseModel):
    totais_por_empresa: List[TotaisPorEmpresa]
    total_geral: TotaisGerais
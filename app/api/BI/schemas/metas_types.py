from pydantic import BaseModel
from typing import List, Literal, Optional

# 📥 Requisição com datas e empresas
class TypeConsultaMetaRequest(BaseModel):
    dataInicio: str
    dataFinal: Optional[str] = None
    empresas: List[str]
    fatorCrescimento: Optional[float] = 0.06

# 📤 Totais por empresa (agora com tipo da meta)
class TypeTotaisPorEmpresaMetaResponse(BaseModel):
    codempresa: str
    tipo: Literal['metaVenda', 'limiteCompra', 'metaMargem']
    valorMeta: float

# 📤 Total geral por tipo
class TotalGeralMeta(BaseModel):
    tipo: str  # mesmo tipo acima
    valorMeta: float

# 📤 Resposta completa
class TypeDashboardMetaReturn(BaseModel):
    totais_por_empresa: List[TypeTotaisPorEmpresaMetaResponse]
    total_geral: List[TotalGeralMeta]

class TypeInserirMetaRequest(BaseModel):
    empresa: str
    data: str  # formato YYYY-MM-DD
    tipo: Literal['metaVenda', 'limiteCompra', 'metaMargem']
    valor: float

class MetaDiaria(BaseModel):
    data: str
    meta_gerada: float

class MetasEmpresa(BaseModel):
    empresa: str
    metas: List[MetaDiaria]

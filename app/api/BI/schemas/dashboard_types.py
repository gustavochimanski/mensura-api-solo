# app/schemas/dashboard_types.py
from pydantic import BaseModel
from typing import List, Optional

from app.api.BI.schemas.compras_types import ConsultaMovimentoCompraResponse, CompraDetalhadaResponse
from app.api.BI.schemas.departamento_schema import VendasPorDepartamento, VendasPorEmpresaComDepartamentos
from app.api.BI.schemas.meio_pagamento_types import MeioPagamentoResponseFinal
from app.api.BI.schemas.vendas.resumoVendas import TotaisGerais, TotaisPorEmpresa
from app.api.BI.schemas.vendas.vendasPorHoraTypes import TypeVendaPorHoraComTotalGeralResponse
from app.api.BI.schemas.metas_types import TypeDashboardMetaReturn
from app.api.BI.schemas.vendas.vendaDetalhadaTypes import TypeVendaDetalhadaResponse


class TypeDashboardRequest(BaseModel):
    empresas: List[str]
    dataInicio: str  # 'YYYY-MM-DD'
    dataFinal: str
    situacao: Optional[str] = None
    status_venda: Optional[str] = None
    cod_vendedor: Optional[str] = None

class TypeRelacao(BaseModel):
    relacaoValue: float
    relacaoPorcentagem: float

class TypeDashboardResponse(BaseModel):
    totais_por_empresa: List[TotaisPorEmpresa]
    total_geral: TotaisGerais
    periodo_anterior: List[TotaisPorEmpresa]
    relacao: TypeRelacao
    metas: TypeDashboardMetaReturn
    compras: ConsultaMovimentoCompraResponse
    vendaDetalhada: TypeVendaDetalhadaResponse
    compraDetalhada: CompraDetalhadaResponse
    vendaPorHora: TypeVendaPorHoraComTotalGeralResponse
    meios_pagamento: MeioPagamentoResponseFinal
    departamento_geral: List[VendasPorDepartamento]
    departamento_empresa: List[VendasPorEmpresaComDepartamentos]


# app/api/pdv/services/meio_pagamento_service.py

from datetime import datetime
from sqlalchemy.orm import Session

from app.api.BI.repositories.meio_pagamento_repo import MeioPagamentoRepository
from app.api.BI.schemas.meio_pagamento_types import (
    MeioPagamentoResumoResponse,
    MeioPagamentoResponseFinal,
    MeioPagamentoPorEmpresa,
)

class MeioPagamentoPDVService:
    def __init__(self, db: Session):
        self.db = db

    def consulta_meios_pagamento_dashboard(
        self,
        empresas: list[str],
        data_inicio: str,
        data_fim: str,
    ) -> MeioPagamentoResponseFinal:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

        repo = MeioPagamentoRepository(self.db)

        # 1) Consulta os dados por empresa
        por_empresa_raw = repo.get_resumo_por_empresa(empresas, dt_inicio, dt_fim)

        # 2) Agrupa por empresa
        agrupado: dict[str, list[MeioPagamentoResumoResponse]] = {}
        for row in por_empresa_raw:
            cod = str(row.empresa)
            agrupado.setdefault(cod, []).append(
                MeioPagamentoResumoResponse(
                    tipo=row.tipo or "??",
                    descricao=row.descricao or "DESCONHECIDO",
                    valor_total=float(row.valor_total or 0),
                )
            )
        por_empresa = [
            MeioPagamentoPorEmpresa(empresa=emp, meios=meios)
            for emp, meios in agrupado.items()
        ]

        # 3) Calcula o total geral SOMANDO todos os valores dos meios de cada empresa
        totais_dict: dict[tuple[str, str], float] = {}
        for empresa in por_empresa:
            for meio in empresa.meios:
                key = (meio.tipo, meio.descricao)
                totais_dict[key] = totais_dict.get(key, 0) + meio.valor_total

        total_geral = [
            MeioPagamentoResumoResponse(tipo=tipo, descricao=descricao, valor_total=valor)
            for (tipo, descricao), valor in totais_dict.items()
        ]

        # 4) Retorna tudo
        return MeioPagamentoResponseFinal(
            total_geral=total_geral,
            por_empresa=por_empresa
        )

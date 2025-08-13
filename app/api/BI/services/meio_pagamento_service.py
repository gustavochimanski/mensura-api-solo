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

        # 🔥 Agora usamos a query COMPLETA (total, retiradas, qtde) AGRUPADA POR EMPRESA
        rows = repo.get_resumo_por_empresa_completo(empresas, dt_inicio, dt_fim)

        # Monta por_empresa
        agrupado_por_empresa: dict[str, list[MeioPagamentoResumoResponse]] = {}
        for r in rows:
            empresa    = str(r.empresa)
            cod        = str(r.codmeiopgto) if r.codmeiopgto is not None else "??"
            descricao  = r.descricao or "DESCONHECIDO"
            total      = float(r.total or 0)
            retiradas  = float(r.retiradas or 0)
            qtde       = int(r.qtde or 0)

            agrupado_por_empresa.setdefault(empresa, []).append(
                MeioPagamentoResumoResponse(
                    tipo=cod,
                    descricao=descricao,
                    valor_total=total,
                    retiradas=retiradas,
                    qtde=qtde,
                )
            )

        por_empresa = [
            MeioPagamentoPorEmpresa(empresa=emp, meios=meios)
            for emp, meios in agrupado_por_empresa.items()
        ]

        # total_geral = soma dos por_empresa (agrega por (tipo, descricao))
        totais_dict: dict[tuple[str, str], dict[str, float]] = {}
        for emp in por_empresa:
            for meio in emp.meios:
                key = (meio.tipo, meio.descricao)
                acc = totais_dict.setdefault(key, {"valor_total": 0.0, "retiradas": 0.0, "qtde": 0.0})
                acc["valor_total"] += meio.valor_total
                acc["retiradas"]   += meio.retiradas
                acc["qtde"]        += meio.qtde

        total_geral = [
            MeioPagamentoResumoResponse(
                tipo=tipo, descricao=desc,
                valor_total=vals["valor_total"],
                retiradas=vals["retiradas"],
                qtde=int(vals["qtde"]),
            )
            for (tipo, desc), vals in totais_dict.items()
        ]

        return MeioPagamentoResponseFinal(
            total_geral=total_geral,
            por_empresa=por_empresa
        )

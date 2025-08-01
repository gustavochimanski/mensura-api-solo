from datetime import datetime
from typing import List, Dict, Tuple

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
        empresas: List[str],
        data_inicio: str,
        data_fim: str,
    ) -> MeioPagamentoResponseFinal:
        # 1) Converte as strings para objetos date
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

        repo = MeioPagamentoRepository(self.db)

        # 2) Consulta única por empresa (já filtrado e mapeado por tipo)
        por_empresa_raw = repo.get_resumo_por_empresa(empresas, dt_inicio, dt_fim)

        # 3) Agrupa por empresa
        empresa_map: Dict[str, List[MeioPagamentoResumoResponse]] = {}
        for row in por_empresa_raw:
            cod_empresa = str(row.empresa)
            empresa_map.setdefault(cod_empresa, []).append(
                MeioPagamentoResumoResponse(
                    tipo=row.tipo or "??",
                    descricao=row.descricao or "DESCONHECIDO",
                    valor_total=float(row.valor_total or 0)
                )
            )

        por_empresa = [
            MeioPagamentoPorEmpresa(empresa=empresa, meios=meios)
            for empresa, meios in empresa_map.items()
        ]

        # 4) Recalcula total geral somando todos os valores de todas as empresas
        totais_dict: Dict[Tuple[str, str], float] = {}
        for row in por_empresa_raw:
            key = (row.tipo or "??", row.descricao or "DESCONHECIDO")
            totais_dict[key] = totais_dict.get(key, 0) + float(row.valor_total or 0)

        total_geral = sorted([
            MeioPagamentoResumoResponse(
                tipo=tipo,
                descricao=descricao,
                valor_total=valor
            )
            for (tipo, descricao), valor in totais_dict.items()
        ], key=lambda x: x.valor_total, reverse=True)  # opcional: ordena por valor desc

        # 5) Retorna o objeto final
        return MeioPagamentoResponseFinal(
            total_geral=total_geral,
            por_empresa=por_empresa
        )

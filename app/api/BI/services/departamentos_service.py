from collections import defaultdict
from decimal import Decimal
from sqlalchemy.orm import Session

from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import (
    VendasPorDepartamento,
    VendasPorEmpresaComDepartamentos,
)


class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]

        if not codigos_subempresas:
            return []

        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, codigos_subempresas)

        # Mapeia código para nome de empresa
        mapa_empresa_nome = {s.sube_codigo: s.sube_descricao for s in subempresas}

        # Mapeia os resultados por empresa
        agrupado_por_empresa: dict[str, list[VendasPorDepartamento]] = defaultdict(list)

        for cod_empresa, cod_departamento, total in vendas:
            nome_empresa = mapa_empresa_nome.get(cod_empresa)
            nome_departamento = mapa_empresa_nome.get(cod_departamento)

            if nome_empresa and nome_departamento:
                agrupado_por_empresa[nome_empresa].append(
                    VendasPorDepartamento(
                        departamento=nome_departamento,
                        total_vendas=float(total)
                    )
                )

        # Monta lista final
        return [
            VendasPorEmpresaComDepartamentos(
                empresa=nome,
                departamentos=departamentos
            )
            for nome, departamentos in agrupado_por_empresa.items()
        ]

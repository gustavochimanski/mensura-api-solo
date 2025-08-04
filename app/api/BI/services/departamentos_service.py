# app/api/BI/services/departamentos_service.py
from collections import defaultdict
from sqlalchemy.orm import Session

from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import (
    VendasPorDepartamento,
    VendasPorEmpresaComDepartamentos,
)
from app.utils.logger import logger


class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos_geral(self, ano_mes: str) -> list[VendasPorDepartamento]:
        """
        Retorna total de vendas por departamento (geral, sem separar por empresa)
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]

        if not codigos_subempresas:
            return []

        vendas_por_departamento = self.repo_lpd.get_vendas_por_departamento(ano_mes, codigos_subempresas)

        # Mapeia código → nome para facilitar match
        mapa_cod_nome = {s.sube_codigo: s.sube_descricao for s in subempresas}

        return [
            VendasPorDepartamento(
                departamento=str(dep),  # ou `f"Departamento {dep}"`, algo mais legível
                total_vendas=float(total)
            )
            for dep, total in vendas_por_departamento
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        """
        Retorna total de vendas por empresa e por departamento
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]

        if not codigos_subempresas:
            return []

        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, codigos_subempresas)

        # Mapeia código para nome de empresa e departamento
        mapa_cod_nome = {s.sube_codigo: s.sube_descricao for s in subempresas}

        agrupado_por_empresa: dict[str, list[VendasPorDepartamento]] = defaultdict(list)

        for cod_empresa, cod_departamento, total in vendas:
            nome_empresa = mapa_cod_nome.get(cod_empresa)
            nome_departamento = mapa_cod_nome.get(cod_departamento)

            if nome_empresa and nome_departamento:
                agrupado_por_empresa[nome_empresa].append(
                    VendasPorDepartamento(
                        departamento=nome_departamento,
                        total_vendas=float(total)
                    )
                )

        return [
            VendasPorEmpresaComDepartamentos(
                empresa=nome,
                departamentos=departamentos
            )
            for nome, departamentos in agrupado_por_empresa.items()
        ]

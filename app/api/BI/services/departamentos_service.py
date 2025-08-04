# app/api/BI/services/departamentos_service.py
from collections import defaultdict
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

    def get_mais_vendidos_geral(self, ano_mes: str) -> list[VendasPorDepartamento]:
        """
        (sem mudanças) total geral por departamento
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        vendas = self.repo_lpd.get_vendas_por_departamento(ano_mes, cods)
        return [
            VendasPorDepartamento(departamento=str(dep), total_vendas=float(total))
            for dep, total in vendas
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        """
        Agora retorna para cada empresa (código) sua lista de departamentos (com descrição),
        usando o resultado do repositório diretamente.
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        # 1) busca tuplas (cod_empresa, departamento_desc, total)
        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, cods)
        if not vendas:
            return []

        # 2) agrupa por empresa
        agrupado: dict[str, list[VendasPorDepartamento]] = defaultdict(list)
        for cod_emp, dept_desc, total in vendas:
            agrupado[str(cod_emp)].append(
                VendasPorDepartamento(departamento=dept_desc, total_vendas=float(total))
            )

        # 3) monta a lista final
        return [
            VendasPorEmpresaComDepartamentos(empresa=emp, departamentos=deps)
            for emp, deps in agrupado.items()
        ]

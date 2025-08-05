from collections import defaultdict
from sqlalchemy.orm import Session

from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import (
    VendasPorDepartamento,
    VendasPorEmpresaComDepartamentos,
)
from app.api.public.models.empresa.empresasModel import Empresa
from app.utils.logger import logger


from datetime import datetime

class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos_geral(self, data_inicio: str, data_fim: str) -> list[VendasPorDepartamento]:
        subemps = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subemps if s.sube_codigo is not None]
        if not cods:
            return []

        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

        raw = self.repo_lpd.get_vendas_por_departamento_periodo(cods, dt_inicio, dt_fim)
        mapa_dep = {s.sube_codigo: s.sube_descricao for s in subemps}

        return [
            VendasPorDepartamento(
                departamento=mapa_dep.get(dep),
                total_vendas=float(total)
            )
            for dep, total in raw
            if dep in mapa_dep
        ]

    def get_mais_vendidos(self, data_inicio: str, data_fim: str) -> list[VendasPorEmpresaComDepartamentos]:
        subemps = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subemps if s.sube_codigo is not None]
        if not cods:
            return []

        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento_periodo(cods, dt_inicio, dt_fim)

        rows_emp = (
            self.db
            .query(Empresa.empr_codigo, Empresa.empr_nomereduzido)
            .distinct()
            .all()
        )
        mapa_emp = {str(c).zfill(3): n for c, n in rows_emp}
        mapa_dep = {s.sube_codigo: s.sube_descricao for s in subemps}

        agrupado: dict[str, list[VendasPorDepartamento]] = defaultdict(list)
        for cod_loja, cod_dep, total in vendas:
            key_loja = str(cod_loja).zfill(3)
            nome_loja = mapa_emp.get(key_loja)
            nome_dep = mapa_dep.get(cod_dep)

            if not nome_loja:
                logger.warning(f"Empresa {cod_loja!r} não mapeada em {list(mapa_emp.keys())}")
                continue
            if not nome_dep:
                logger.warning(f"Departamento {cod_dep!r} não mapeado em subempresas")
                continue

            agrupado[key_loja].append(
                VendasPorDepartamento(departamento=nome_dep, total_vendas=float(total))
            )

        return [
            VendasPorEmpresaComDepartamentos(empresa=emp, departamentos=deps)
            for emp, deps in agrupado.items()
        ]

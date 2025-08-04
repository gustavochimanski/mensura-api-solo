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


class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos_geral(self, ano_mes: str) -> list[VendasPorDepartamento]:
        """
        Retorna total de vendas por departamento (geral, sem separar por empresa).
        Só categorias cujos codsubempresa estejam no cadastro de subempresas.
        Nome do departamento vem de subempresas.
        """
        subemps = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subemps if s.sube_codigo is not None]
        if not cods:
            return []

        raw = self.repo_lpd.get_vendas_por_departamento(ano_mes, cods)
        # Mapa de departamento: sube_codigo → sube_descricao
        mapa_dep = {s.sube_codigo: s.sube_descricao for s in subemps}

        return [
            VendasPorDepartamento(
                departamento=mapa_dep.get(dep),
                total_vendas=float(total)
            )
            for dep, total in raw
            if dep in mapa_dep
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        """
        Retorna vendas por empresa e departamento com nomes corretos:
        - filtra categorias pelas subempresas
        - departamento nome vem de subempresas
        - empresa nome vem de EmpresaPublicModel
        """
        # 1) subempresas para filtro de categorias
        subemps = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subemps if s.sube_codigo is not None]
        if not cods:
            return []

        # 2) raw de vendas por loja+departamento
        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, cods)

        # 3) mapa de empresas (001,002..) → nome
        rows_emp = (
            self.db
            .query(Empresa.empr_codigo)
            .distinct()
            .all()
        )
        mapa_emp = {str(c).zfill(3): n for c, n in rows_emp}

        # 4) mapa de departamentos: sube_codigo → sube_descricao
        mapa_dep = {s.sube_codigo: s.sube_descricao for s in subemps}

        # 5) agrupa resultados
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

            agrupado[nome_loja].append(
                VendasPorDepartamento(departamento=nome_dep, total_vendas=float(total))
            )

        # 6) monta resposta final
        return [
            VendasPorEmpresaComDepartamentos(empresa=emp, departamentos=deps)
            for emp, deps in agrupado.items()
        ]

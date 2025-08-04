from collections import defaultdict
from sqlalchemy.orm import Session

from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import (
    VendasPorDepartamento,
    VendasPorEmpresaComDepartamentos,
)
from app.api.public.models.categoriaprod_public_model import CategoriaProdutoPublicModel
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
        Só inclui categorias válidas das subempresas.
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        vendas = self.repo_lpd.get_vendas_por_departamento(ano_mes, cods)
        mapa = {s.sube_codigo: s.sube_descricao for s in subempresas}

        return [
            VendasPorDepartamento(
                departamento=mapa.get(dep),
                total_vendas=float(total)
            )
            for dep, total in vendas
            if dep in mapa
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        """
        Retorna vendas por empresa e departamento com nomes corretos.
        Só inclui categorias válidas das subempresas.
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, cods)

        # mapeia empresas reais (001,002..) → nome
        rows_emp = (
            self.db
            .query(Empresa.empr_codigo, Empresa.empr_nome)
            .distinct()
            .all()
        )
        mapa_emp = {str(cod).zfill(3): nome for cod, nome in rows_emp}

        # mapeia departamentos → nome
        rows_dep = (
            self.db
            .query(
                CategoriaProdutoPublicModel.cate_codsubempresa,
                CategoriaProdutoPublicModel.cate_descricao
            )
            .filter(CategoriaProdutoPublicModel.cate_codsubempresa.in_(cods))
            .distinct()
            .all()
        )
        mapa_dep = {cod: desc for cod, desc in rows_dep}

        agrupado: dict[str, list[VendasPorDepartamento]] = defaultdict(list)
        for cod_emp, cod_dep, total in vendas:
            key_emp = str(cod_emp).zfill(3)
            nome_emp = mapa_emp.get(key_emp)
            nome_dep = mapa_dep.get(cod_dep)

            if not nome_emp:
                logger.warning(f"Empresa {cod_emp!r} não mapeada em {list(mapa_emp.keys())}")
                continue
            if not nome_dep:
                logger.warning(f"Departamento {cod_dep!r} não mapeado")
                continue

            agrupado[nome_emp].append(
                VendasPorDepartamento(departamento=nome_dep, total_vendas=float(total))
            )

        return [
            VendasPorEmpresaComDepartamentos(empresa=emp, departamentos=deps)
            for emp, deps in agrupado.items()
        ]

# app/api/BI/services/departamentos_service.py
from collections import defaultdict
from sqlalchemy.orm import Session

from app.api.BI.repositories.lpd_repo import LpdRepository
from app.api.BI.repositories.subempresas_repo import SubEmpresasPublicRepository
from app.api.BI.schemas.departamento_schema import (
    VendasPorDepartamento,
    VendasPorEmpresaComDepartamentos,
)
from app.api.public.models.categoriaprod_public_model import CategoriaProdutoPublicModel
from app.utils.logger import logger


class DepartamentosPublicService:
    def __init__(self, db: Session):
        self.db = db
        self.repo_subempresas = SubEmpresasPublicRepository(db)
        self.repo_lpd = LpdRepository(db)

    def get_mais_vendidos_geral(self, ano_mes: str) -> list[VendasPorDepartamento]:
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        vendas = self.repo_lpd.get_vendas_por_departamento(ano_mes, cods)
        return [
            VendasPorDepartamento(
                departamento=str(dep),
                total_vendas=float(total)
            )
            for dep, total in vendas
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        # 1) pega tuplas (cod_empresa, cod_dep, total)
        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, cods)
        if not vendas:
            return []

        # 2) mapeia empresas pelo que veio em subempresas
        mapa_empresas = {str(s.sube_codigo): s.sube_descricao for s in subempresas}

        # 3) extrai todos os departamentos que foram vendidos
        cod_departamentos = {dep for _, dep, _ in vendas}
        # 4) busca nomes desses departamentos
        rows = (
            self.db
            .query(
                CategoriaProdutoPublicModel.cate_codsubempresa,
                CategoriaProdutoPublicModel.cate_descricao
            )
            .filter(CategoriaProdutoPublicModel.cate_codsubempresa.in_(cod_departamentos))
            .distinct()
            .all()
        )
        mapa_departamentos = {cod: desc for cod, desc in rows}

        # 5) agrupa
        agrupado: dict[str, list[VendasPorDepartamento]] = defaultdict(list)
        for cod_emp, cod_dep, total in vendas:
            key_emp = str(cod_emp)
            nome_emp = mapa_empresas.get(key_emp)
            nome_dep = mapa_departamentos.get(cod_dep)

            if not nome_emp:
                logger.warning(f"Empresa {cod_emp!r} não mapeada")
                continue
            if not nome_dep:
                logger.warning(f"Departamento {cod_dep!r} não mapeado")
                continue

            agrupado[nome_emp].append(
                VendasPorDepartamento(departamento=nome_dep, total_vendas=float(total))
            )

        # 6) monta lista final
        return [
            VendasPorEmpresaComDepartamentos(empresa=emp, departamentos=deps)
            for emp, deps in agrupado.items()
        ]

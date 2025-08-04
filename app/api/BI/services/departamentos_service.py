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
        Usa subempresas apenas para filtro, mapeia depois para nomes.
        """
        subempresas = self.repo_subempresas.get_all_isvendas()
        codigos_subempresas = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not codigos_subempresas:
            return []

        vendas = self.repo_lpd.get_vendas_por_departamento(ano_mes, codigos_subempresas)

        # Mapa codigo_subempresa → descricao
        mapa_cod_nome = {s.sube_codigo: s.sube_descricao for s in subempresas}

        return [
            VendasPorDepartamento(
                departamento=mapa_cod_nome.get(dep),  # nome do departamento
                total_vendas=float(total)
            )
            for dep, total in vendas
            if dep in mapa_cod_nome
        ]

    def get_mais_vendidos(self, ano_mes: str) -> list[VendasPorEmpresaComDepartamentos]:
        """
        Retorna vendas por empresa e departamento com nomes corretos.
        1) Filtra departamentos pelas subempresas
        2) Busca raw de vendas por empresa+departamento
        3) Mapeia empresas reais (001,002..) para nome
        4) Mapeia departamentos (codsubempresa) para nome
        5) Agrupa e devolve Pydantic models
        """
        # 1) pega lista de subempresas para filtrar departamentos
        subempresas = self.repo_subempresas.get_all_isvendas()
        cods = [s.sube_codigo for s in subempresas if s.sube_codigo is not None]
        if not cods:
            return []

        # 2) dados crus: lista de tuples (empresa, departamento, total)
        vendas = self.repo_lpd.get_vendas_por_empresa_e_departamento(ano_mes, cods)

        # 3) Mapa código → nome de empresa (tabela de empresas reais)
        rows_emp = (
            self.db
            .query(
                Empresa.empr_codigo,   # ex: 1, 2, 4
                Empresa.empr_nome      # ex: "Golfinho"
            )
            .distinct()
            .all()
        )
        # padroniza para '001', '002', etc
        mapa_empresas = {str(cod).zfill(3): nome for cod, nome in rows_emp}

        # 4) Mapa código → nome de departamento
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
        mapa_departamentos = {cod: desc for cod, desc in rows_dep}

        # 5) Agrupar em dict
        agrupado: dict[str, list[VendasPorDepartamento]] = defaultdict(list)
        for cod_emp_raw, cod_dep, total in vendas:
            key_emp = str(cod_emp_raw).zfill(3)
            nome_emp = mapa_empresas.get(key_emp)
            nome_dep = mapa_departamentos.get(cod_dep)

            if not nome_emp:
                logger.warning(f"Empresa {cod_emp_raw!r} não mapeada em {list(mapa_empresas.keys())}")
                continue
            if not nome_dep:
                logger.warning(f"Departamento {cod_dep!r} não mapeado")
                continue

            agrupado[nome_emp].append(
                VendasPorDepartamento(departamento=nome_dep, total_vendas=float(total))
            )

        # 6) Monta resultado final
        return [
            VendasPorEmpresaComDepartamentos(empresa=emp, departamentos=deps)
            for emp, deps in agrupado.items()

        ]
